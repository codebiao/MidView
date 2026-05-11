"""Circular wafer visualization widget using QGraphicsView."""

from __future__ import annotations

import math
import numpy as np
from PySide6.QtWidgets import (
    QGraphicsView,
    QGraphicsScene,
    QGraphicsEllipseItem,
    QGraphicsPathItem,
    QGraphicsPolygonItem,
    QGraphicsSimpleTextItem,
    QGraphicsItem,
    QMenu,
    QLabel,
    QRubberBand,
)
from PySide6.QtCore import Qt, Signal, QPointF, QRectF, QSize
from PySide6.QtGui import (
    QPainter,
    QPen,
    QColor,
    QBrush,
    QPainterPath,
    QPolygonF,
    QImage,
    QPixmap,
    QAction,
    QFont,
)

from backend.models import Defect, Event, PacketRawMeta, PacketImage
from backend.data_load.event_loader import get_event_chain

RADIUS_MAX = 150000.0
WENC_MAX = 262144.0
XENC_MAX = 187500.0
XENC_START = 2400.0
NEARBY_SCREEN_PX = 25.0


def wenc_xenc_to_xy(wenc: float, xenc: float) -> tuple[float, float]:
    angle = 2.0 * math.pi * wenc / WENC_MAX
    r = RADIUS_MAX * (XENC_MAX - xenc) / (XENC_MAX - XENC_START)
    x = r * math.cos(angle)
    y = r * math.sin(angle)
    return x, y


def _interp_wenc(w1: float, w2: float, t: float) -> float:
    """Interpolate wenc along the shortest path (handles circular wrap-around)."""
    diff = w2 - w1
    half = WENC_MAX / 2.0
    if diff > half:
        diff -= WENC_MAX
    elif diff < -half:
        diff += WENC_MAX
    return (w1 + diff * t) % WENC_MAX


class DefectItem(QGraphicsEllipseItem):
    """A defect data point with screen-constant size and selection support."""

    _dot_radius = 2.0
    _hover_radius = 4.0
    _select_radius = 6.0

    _color_normal = QColor("#dc3545")
    _color_hover = QColor("#ff8787")
    _color_select = QColor("#2563a0")

    def __init__(self, defect: Defect):
        self.defect = defect
        self._selected = False
        r = self._dot_radius
        super().__init__(-r, -r, r * 2, r * 2)
        self._apply_style(self._color_normal, self._dot_radius)
        self.setZValue(10)
        self.setAcceptHoverEvents(True)
        self.setFlag(
            QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations, True
        )

    def _apply_style(self, color: QColor, radius: float):
        self.setPen(Qt.PenStyle.NoPen)
        self.setBrush(QBrush(color))
        self.setRect(-radius, -radius, radius * 2, radius * 2)

    def shape(self) -> QPainterPath:
        p = QPainterPath()
        p.addEllipse(QPointF(0, 0), self._hover_radius, self._hover_radius)
        return p

    def set_selected(self, selected: bool):
        self._selected = selected
        if selected:
            self._apply_style(self._color_select, self._select_radius)
            self.setZValue(100)
        else:
            self._apply_style(self._color_normal, self._dot_radius)
            self.setZValue(10)

    def hoverEnterEvent(self, event):
        if not self._selected:
            self._apply_style(self._color_hover, self._hover_radius)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        if not self._selected:
            self._apply_style(self._color_normal, self._dot_radius)
        super().hoverLeaveEvent(event)


class EventRegionItem(QGraphicsPolygonItem):
    """A clickable event region that shows event info on click."""

    _normal_pen = QPen(QColor("#5ba0d0"))
    _normal_pen.setCosmetic(True)
    _normal_pen.setWidthF(1.2)

    _select_pen = QPen(QColor("#1a5a90"))
    _select_pen.setCosmetic(True)
    _select_pen.setWidthF(2.5)

    _normal_brush = QBrush(Qt.BrushStyle.NoBrush)
    _select_brush = QBrush(QColor(26, 90, 144, 35))

    _expand_pen = QPen(QColor(128, 128, 128, 128))
    _expand_pen.setCosmetic(True)
    _expand_pen.setWidthF(1.0)
    _expand_brush = QBrush(QColor(160, 160, 160, 40))

    def __init__(
        self,
        event: Event,
        polygon: QPolygonF,
        expanded_polygon: QPolygonF | None = None,
    ):
        super().__init__(polygon)
        self.event = event
        self._region_selected = False
        self.setPen(self._normal_pen)
        self.setBrush(self._normal_brush)
        self.setAcceptHoverEvents(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._expanded_item: QGraphicsPolygonItem | None = None
        if expanded_polygon is not None and not expanded_polygon.isEmpty():
            self._expanded_item = QGraphicsPolygonItem(expanded_polygon, self)
            self._expanded_item.setPen(self._expand_pen)
            self._expanded_item.setBrush(self._expand_brush)
            self._expanded_item.setVisible(False)

    def set_region_selected(self, selected: bool):
        self._region_selected = selected
        if selected:
            self.setPen(self._select_pen)
            self.setBrush(self._select_brush)
            if self._expanded_item is not None:
                self._expanded_item.setVisible(True)
        else:
            self.setPen(self._normal_pen)
            self.setBrush(self._normal_brush)
            if self._expanded_item is not None:
                self._expanded_item.setVisible(False)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            view = self.scene().views()[0]
            if hasattr(view, "_on_event_item_clicked"):
                view._on_event_item_clicked(self)
            event.accept()
            return
        super().mousePressEvent(event)


class CircularView(QGraphicsView):
    """Main circular visualization view."""

    defect_clicked = Signal(Defect)
    defect_context_requested = Signal(Defect)
    event_region_clicked = Signal(Event)
    view_all_events_requested = Signal()
    view_all_spiral_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)

        self.setRenderHints(
            QPainter.RenderHint.Antialiasing
            | QPainter.RenderHint.SmoothPixmapTransform
        )
        self.setViewportUpdateMode(
            QGraphicsView.ViewportUpdateMode.FullViewportUpdate
        )
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(
            QGraphicsView.ViewportAnchor.AnchorUnderMouse
        )
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.setBackgroundBrush(QBrush(QColor("#f5f4f1")))
        self.setFrameShape(QGraphicsView.Shape.NoFrame)
        self.setMouseTracking(True)
        self.viewport().setCursor(Qt.CursorShape.ArrowCursor)

        self._defect_items: dict[int, DefectItem] = {}
        self._event_polygons: list[QGraphicsPolygonItem] = []
        self._packet_polygons: list[QGraphicsPolygonItem] = []
        self._spiral_items: list[QGraphicsPathItem] = []
        self._packet_labels: list[QGraphicsSimpleTextItem] = []
        self._spiral_drawn: bool = False
        self._circle_item: QGraphicsEllipseItem | None = None
        self._pixmap_items: list[QGraphicsItem] = []
        self._selected_item: DefectItem | None = None

        self._defect_array: list[Defect] = []
        self._event_array: list[Event] = []
        self._packet_raw_meta_array: list[PacketRawMeta] = []
        self._shown_event_defects: set[int] = set()

        self._draw_base_geometry()
        self._scene.setSceneRect(
            -RADIUS_MAX * 2, -RADIUS_MAX * 2, RADIUS_MAX * 4, RADIUS_MAX * 4
        )

        self._coord_label = QLabel(self)
        self._coord_label.setStyleSheet(
            "background: rgba(250,250,248,215); color: #333;"
            "padding: 2px 6px; border-radius: 4px; font-size: 11px;"
        )
        self._coord_label.hide()

        self._scale_label = QLabel(self)
        self._scale_label.setStyleSheet(
            "background: rgba(250,250,248,215); color: #333;"
            "padding: 2px 6px; border-radius: 4px; font-size: 11px;"
            "font-family: monospace;"
        )
        self._scale_label.hide()

        self._rubber_band: QRubberBand | None = None
        self._rubber_origin: QPointF | None = None
        self._rubber_button = Qt.MouseButton.NoButton
        self._suppress_context: bool = False

        self._mode = "pan"
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)

        self._selected_event_item: EventRegionItem | None = None

    def _on_event_item_clicked(self, item: EventRegionItem):
        """Handle event region click — select, or deselect if already selected."""
        if self._selected_event_item is item:
            self._selected_event_item.set_region_selected(False)
            self._selected_event_item = None
            self.event_region_clicked.emit(None)
        else:
            if self._selected_event_item is not None:
                self._selected_event_item.set_region_selected(False)
            self._selected_event_item = item
            item.set_region_selected(True)
            self.event_region_clicked.emit(item.event)

    def _select_event_item(self, item: EventRegionItem):
        if self._selected_event_item is not None and self._selected_event_item is not item:
            self._selected_event_item.set_region_selected(False)
        self._selected_event_item = item
        item.set_region_selected(True)

    def _on_fit_view(self):
        self.fit_circle()
        self._update_scale_bar()

    def showEvent(self, event):
        super().showEvent(event)
        self.fit_circle()
        self._update_scale_bar()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_scale_bar()

    def _draw_base_geometry(self):
        """Draw the outer circle outline (no fill) and crosshair axes."""
        pen = QPen(QColor("#000000"))
        pen.setCosmetic(True)
        pen.setWidthF(2.0)
        self._circle_item = QGraphicsEllipseItem(
            -RADIUS_MAX, -RADIUS_MAX, RADIUS_MAX * 2, RADIUS_MAX * 2
        )
        self._circle_item.setPen(pen)
        self._circle_item.setBrush(Qt.BrushStyle.NoBrush)
        self._circle_item.setZValue(0)
        self._scene.addItem(self._circle_item)

        axis_pen = QPen(QColor("#e0e0e0"))
        axis_pen.setCosmetic(True)
        axis_pen.setWidthF(0.5)
        axis_pen.setStyle(Qt.PenStyle.DashLine)
        self._scene.addLine(-RADIUS_MAX, 0, RADIUS_MAX, 0, axis_pen)
        self._scene.addLine(0, -RADIUS_MAX, 0, RADIUS_MAX, axis_pen)

    def fit_circle(self):
        """Fit the entire circle in view with no margin."""
        rect = QRectF(
            -RADIUS_MAX, -RADIUS_MAX, RADIUS_MAX * 2, RADIUS_MAX * 2
        )
        self.fitInView(rect, Qt.AspectRatioMode.KeepAspectRatio)

    def draw_spiral_from_packets(
        self, progress_callback=None
    ) -> int:
        """Draw spiral through all packet data."""
        for item in self._spiral_items:
            self._scene.removeItem(item)
        self._spiral_items.clear()
        for lbl in self._packet_labels:
            self._scene.removeItem(lbl)
        self._packet_labels.clear()

        packets = self._packet_raw_meta_array
        total = len(packets)
        if not packets:
            if progress_callback:
                progress_callback(total, total)
            return 0

        pen_a = QPen(QColor(160, 160, 160, 179))
        pen_a.setCosmetic(True); pen_a.setWidthF(1.2)
        pen_b = QPen(QColor(50, 50, 50, 179))
        pen_b.setCosmetic(True); pen_b.setWidthF(1.2)

        path_a = QPainterPath()
        path_b = QPainterPath()

        drawn = 0
        for seg_i, pkt in enumerate(packets):
            xs, ys = wenc_xenc_to_xy(pkt.wenc_left, pkt.xenc_outer)
            xe, ye = wenc_xenc_to_xy(pkt.wenc_right, pkt.xenc_inner)

            cur = path_a if (seg_i % 2 == 0) else path_b
            cur.moveTo(xs, ys)
            cur.lineTo(xe, ye)

            drawn += 1
            if progress_callback:
                progress_callback(drawn, total)

        if progress_callback:
            progress_callback(total, total)

        item_a = QGraphicsPathItem(path_a)
        item_a.setPen(pen_a); item_a.setZValue(1)
        self._scene.addItem(item_a)
        item_b = QGraphicsPathItem(path_b)
        item_b.setPen(pen_b); item_b.setZValue(1)
        self._scene.addItem(item_b)
        self._spiral_items = [item_a, item_b]

        # start marker
        if packets:
            sx, sy = wenc_xenc_to_xy(
                packets[0].wenc_left, packets[0].xenc_outer
            )
            marker = QGraphicsEllipseItem(
                sx - 200, sy - 200, 400, 400
            )
            marker.setPen(QPen(QColor(0, 0, 0, 0)))
            marker.setBrush(QBrush(QColor(34, 139, 34, 200)))
            marker.setZValue(3)
            self._scene.addItem(marker)
            self._spiral_items.append(marker)

        # labels: packet_id at center of each packet's region
        label_font = QFont()
        label_font.setFamily("monospace")
        label_font.setPointSize(12)
        label_color = QColor(140, 140, 140)
        self._packet_labels = []
        for pkt in packets:
            # center: shortest-path midpoint in wenc
            dw = pkt.wenc_right - pkt.wenc_left
            if dw > WENC_MAX / 2.0:
                dw -= WENC_MAX
            elif dw < -WENC_MAX / 2.0:
                dw += WENC_MAX
            wc = pkt.wenc_left + dw / 2.0
            xc = (pkt.xenc_outer + pkt.xenc_inner) / 2.0
            cx, cy = wenc_xenc_to_xy(wc, xc)

            label = QGraphicsSimpleTextItem(str(pkt.packet_id))
            label.setFont(label_font)
            label.setBrush(label_color)
            label.setPos(cx, cy)
            label.setZValue(2)
            self._scene.addItem(label)
            self._packet_labels.append(label)

        self._spiral_drawn = True

        return 0

    def load_data(
        self,
        defect_array: list[Defect],
        packet_raw_meta_array: list[PacketRawMeta],
    ):
        """Load and display defect data. Spiral is lazy-loaded."""
        self._defect_array = defect_array
        self._event_array = []
        self._packet_raw_meta_array = packet_raw_meta_array

        self.clear_data_items()
        self.draw_defects()

    def clear_data_items(self):
        """Remove all data-dependent items."""
        for item in self._defect_items.values():
            self._scene.removeItem(item)
        self._defect_items.clear()

        for item in self._event_polygons:
            self._scene.removeItem(item)
        self._event_polygons.clear()

        for item in self._packet_polygons:
            self._scene.removeItem(item)
        self._packet_polygons.clear()

        for item in self._pixmap_items:
            self._scene.removeItem(item)
        self._pixmap_items.clear()

        self._selected_item = None
        self._shown_event_defects.clear()
        for item in self._spiral_items:
            self._scene.removeItem(item)
        self._spiral_items.clear()
        for lbl in self._packet_labels:
            self._scene.removeItem(lbl)
        self._packet_labels.clear()
        self._packet_raw_meta_array = []
        self._event_array = []
        self._spiral_drawn = False

    def draw_packet_regions(self):
        """Draw packet boundary regions."""
        pen = QPen(QColor("#dee2e6"))
        pen.setCosmetic(True)
        pen.setWidthF(0.5)
        brush = QBrush(QColor(220, 225, 230, 40))

        for pkt in self._packet_raw_meta_array:
            poly = self._packet_region_polygon(pkt)
            if poly is None:
                continue
            item = QGraphicsPolygonItem(poly)
            item.setPen(pen)
            item.setBrush(brush)
            item.setZValue(2)
            self._scene.addItem(item)
            self._packet_polygons.append(item)

    def _packet_region_polygon(
        self, pkt: PacketRawMeta
    ) -> QPolygonF | None:
        """Build a polygon for a packet region from its four corner points."""
        wl, wr = pkt.wenc_left, pkt.wenc_right
        xo, xi = pkt.xenc_outer, pkt.xenc_inner

        n_samples = 8
        points_outer = []
        points_inner = []

        for i in range(n_samples):
            frac = i / (n_samples - 1)
            w = wl + frac * (wr - wl)
            points_outer.append(QPointF(*wenc_xenc_to_xy(w, xo)))
            points_inner.append(QPointF(*wenc_xenc_to_xy(w, xi)))

        poly = QPolygonF()
        for pt in points_outer:
            poly.append(pt)
        for pt in reversed(points_inner):
            poly.append(pt)

        return poly

    def draw_defects(self):
        """Place defect points via (x_encoder, w_encoder) coordinate transform."""
        for defect in self._defect_array:
            x, y = wenc_xenc_to_xy(defect.w_encoder, defect.x_encoder)
            item = DefectItem(defect)
            item.setPos(x, y)
            self._scene.addItem(item)
            self._defect_items[defect.index] = item

    def set_mode(self, mode: str):
        self._mode = mode
        if mode == "pan":
            self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        else:
            self.setDragMode(QGraphicsView.DragMode.NoDrag)

    def _deselect_current(self):
        if self._selected_item is not None:
            self._selected_item.set_selected(False)
            self._selected_item = None

    def select_defect_item(self, item: DefectItem):
        """Select one defect item, deselecting the previous."""
        if self._selected_item is not None and self._selected_item is not item:
            self._selected_item.set_selected(False)
        self._selected_item = item
        item.set_selected(True)

    def _scene_threshold(self) -> float:
        """Convert NEARBY_SCREEN_PX to scene units at current zoom level."""
        p1 = self.mapToScene(0, 0)
        p2 = self.mapToScene(int(NEARBY_SCREEN_PX), 0)
        return abs(p2.x() - p1.x())

    def _find_nearby_defect(self, scene_pos: QPointF) -> DefectItem | None:
        """Return the nearest defect within adaptive screen-pixel distance."""
        if not self._defect_items:
            return None

        threshold = self._scene_threshold()
        best_item = None
        best_dist_sq = threshold * threshold

        for item in self._defect_items.values():
            dp = item.scenePos() - scene_pos
            d_sq = dp.x() * dp.x() + dp.y() * dp.y()
            if d_sq < best_dist_sq:
                best_dist_sq = d_sq
                best_item = item

        return best_item

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            scene_pos = self.mapToScene(event.pos())

            if self._mode == "zoom_rect":
                self._rubber_origin = event.pos()
                if self._rubber_band is None:
                    self._rubber_band = QRubberBand(
                        QRubberBand.Shape.Rectangle, self
                    )
                self._rubber_band.setGeometry(
                    event.pos().x(), event.pos().y(), 0, 0
                )
                self._rubber_band.show()
                self._rubber_button = Qt.LeftButton
                event.accept()
                return

            # 1. check for nearby defect first (small dot, narrow threshold)
            item = self._find_nearby_defect(scene_pos)
            if item is not None:
                if item is self._selected_item:
                    self._deselect_current()
                    self.defect_clicked.emit(None)
                else:
                    self.defect_clicked.emit(item.defect)
                event.accept()
                return

            # 2. no defect hit — find event regions, pick smallest (most nested)
            candidates = [
                it for it in self._scene.items(scene_pos)
                if isinstance(it, EventRegionItem)
            ]
            if candidates:
                best = min(
                    candidates,
                    key=lambda it: it.polygon().boundingRect().width()
                    * it.polygon().boundingRect().height(),
                )
                self._on_event_item_clicked(best)
                event.accept()
                return

        elif event.button() == Qt.RightButton:
            # start rubber-band zoom (right-drag)
            self._rubber_origin = event.pos()
            if self._rubber_band is None:
                self._rubber_band = QRubberBand(
                    QRubberBand.Shape.Rectangle, self
                )
            self._rubber_band.setGeometry(
                event.pos().x(), event.pos().y(), 0, 0
            )
            self._rubber_band.show()
            self._rubber_button = Qt.RightButton
            event.accept()
            return

        super().mousePressEvent(event)

    def _update_scale_bar(self):
        """Compute scale bar: nice round distance in μm for ~80 screen px."""
        p1 = self.mapToScene(0, 0)
        p2 = self.mapToScene(80, 0)
        scene_dist = abs(p2.x() - p1.x())

        # round to a nice number
        nice = [1, 2, 5, 10, 20, 50, 100, 200, 500,
                1000, 2000, 5000, 10000, 20000, 50000, 100000]
        best = nice[0]
        for n in nice:
            if n <= scene_dist:
                best = n
        screen_px = 80.0 * best / scene_dist if scene_dist > 0 else 80

        if best >= 1000:
            label = f"{best / 1000:.0f}k"
        else:
            label = str(best)

        bar_width = max(6, int(screen_px / 7))
        bar = "│" + "─" * bar_width + "│"
        self._scale_label.setText(f"{bar} {label} μm")
        self._scale_label.adjustSize()
        self._position_overlays()

    def _position_overlays(self):
        vp = self.viewport()
        if vp is None:
            return
        sw = self._scale_label.width()
        cw = self._coord_label.width()
        self._scale_label.move(vp.width() - cw - sw - 16, 8)
        self._coord_label.move(vp.width() - cw - 8, 8)
        self._scale_label.show()
        self._coord_label.show()

    def mouseMoveEvent(self, event):
        scene_pos = self.mapToScene(event.pos())
        self._coord_label.setText(
            f"X: {scene_pos.x():.1f}  Y: {scene_pos.y():.1f}"
        )
        self._coord_label.adjustSize()
        self._position_overlays()

        if (
            self._rubber_band is not None
            and self._rubber_origin is not None
        ):
            x = min(self._rubber_origin.x(), event.pos().x())
            y = min(self._rubber_origin.y(), event.pos().y())
            w = abs(event.pos().x() - self._rubber_origin.x())
            h = abs(event.pos().y() - self._rubber_origin.y())
            self._rubber_band.setGeometry(x, y, w, h)

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if (
            self._rubber_band is not None
            and self._rubber_origin is not None
        ):
            self._rubber_band.hide()
            rect = self._rubber_band.geometry()
            btn = getattr(self, "_rubber_button", Qt.LeftButton)

            if btn == Qt.RightButton and rect.width() <= 4 and rect.height() <= 4:
                # right-click without drag → context menu on defect
                scene_pos = self.mapToScene(event.pos())
                item = (
                    self._find_nearby_defect(scene_pos)
                    if self._defect_items
                    else None
                )
                if item is not None:
                    self._last_right_click_global = self.mapToGlobal(
                        event.pos()
                    )
                    self.defect_clicked.emit(item.defect)
                    self.defect_context_requested.emit(item.defect)
            elif rect.width() > 4 and rect.height() > 4:
                top_left = self.mapToScene(rect.topLeft())
                bottom_right = self.mapToScene(rect.bottomRight())
                scene_rect = QRectF(top_left, bottom_right)
                self.fitInView(
                    scene_rect, Qt.AspectRatioMode.KeepAspectRatio
                )
                if btn == Qt.LeftButton:
                    self.scale(0.5, 0.5)
                elif btn == Qt.RightButton:
                    self._suppress_context = True

            self._rubber_origin = None
            self._rubber_button = Qt.NoButton
            event.accept()
            self._update_scale_bar()
            return
        super().mouseReleaseEvent(event)

    def wheelEvent(self, event):
        """Zoom in/out with mouse wheel."""
        factor = 1.15
        if event.angleDelta().y() < 0:
            factor = 1.0 / factor
        self.scale(factor, factor)
        self._update_scale_bar()

    def contextMenuEvent(self, event):
        """Custom context menu on the view background."""
        if self._suppress_context:
            self._suppress_context = False
            return
        menu = QMenu(self)

        fit_view = QAction("Fit View", self)
        fit_view.triggered.connect(self._on_fit_view)
        menu.addAction(fit_view)

        menu.addSeparator()

        view_events = QAction("View All Events", self)
        view_events.triggered.connect(self._view_all_events)
        menu.addAction(view_events)

        view_spiral = QAction("View All Spiral", self)
        view_spiral.triggered.connect(self._view_all_spiral)
        menu.addAction(view_spiral)

        menu.addSeparator()

        clear_events = QAction("Clear All Events", self)
        clear_events.triggered.connect(self._clear_event_regions)
        menu.addAction(clear_events)

        clear_spiral = QAction("Clear All Spiral", self)
        clear_spiral.triggered.connect(self._clear_spiral)
        menu.addAction(clear_spiral)

        clear_images = QAction("Clear All Packet Images", self)
        clear_images.triggered.connect(self._clear_image_overlays)
        menu.addAction(clear_images)

        menu.exec(event.globalPos())

    def _view_all_events(self):
        """Request viewing all events for all defects."""
        self.view_all_events_requested.emit()

    def _clear_spiral(self):
        """Clear spiral lines."""
        for item in self._spiral_items:
            self._scene.removeItem(item)
        self._spiral_items.clear()
        for lbl in self._packet_labels:
            self._scene.removeItem(lbl)
        self._packet_labels.clear()
        self._spiral_drawn = False

    def _view_all_spiral(self):
        """Request lazy-loading and drawing all spiral lines."""
        self.view_all_spiral_requested.emit()

    def show_event_regions(self, defect: Defect, event_array: list[Event]):
        """Draw defect region (red dashed) then event chain regions (light blue)."""
        if defect.index in self._shown_event_defects:
            return
        self._shown_event_defects.add(defect.index)
        self._event_array = event_array

        # 1. draw defect's own region as red dashed rectangle
        defect_pen = QPen(QColor("#dc3545"))
        defect_pen.setCosmetic(True)
        defect_pen.setWidthF(1.5)
        defect_pen.setStyle(Qt.PenStyle.DashLine)
        defect_brush = QBrush(Qt.BrushStyle.NoBrush)

        poly = self._make_region_polygon(
            defect.xenc_outer, defect.xenc_inner,
            defect.wenc_left, defect.wenc_right,
        )
        item = QGraphicsPolygonItem(poly)
        item.setPen(defect_pen)
        item.setBrush(defect_brush)
        # Z set below after chain length is known
        item.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        self._scene.addItem(item)
        self._event_polygons.append(item)

        # 2. draw event chain regions — later items get higher Z for nested-click priority
        root_idx = defect.event_root_index
        chain = get_event_chain(root_idx, event_array)

        # defect red dashed always on top
        item.setZValue(5 + len(chain) + 1)

        for i, evt in enumerate(chain):
            poly = self._make_region_polygon(
                evt.xenc_outer, evt.xenc_inner,
                evt.wenc_left, evt.wenc_right,
            )
            # expanded region using merge counts
            xm = abs(evt.xenc_merge_count)
            wm = abs(evt.wenc_merge_count)
            if xm > 0 or wm > 0:
                expanded_poly = self._make_region_polygon(
                    evt.xenc_outer - xm,
                    evt.xenc_inner + xm,
                    evt.wenc_left - wm,
                    evt.wenc_right + wm,
                )
            else:
                expanded_poly = None
            item = EventRegionItem(evt, poly, expanded_poly)
            item.setZValue(5 + i)
            self._scene.addItem(item)
            self._event_polygons.append(item)

    def _clear_event_regions(self):
        for item in self._event_polygons:
            self._scene.removeItem(item)
        self._event_polygons.clear()
        self._shown_event_defects.clear()

    @staticmethod
    def _make_region_polygon(xo: float, xi: float, wl: float, wr: float) -> QPolygonF:
        """Build a 4-corner polygon from xenc/wenc bounds."""
        tl = QPointF(*wenc_xenc_to_xy(wl, xo))
        tr = QPointF(*wenc_xenc_to_xy(wr, xo))
        br = QPointF(*wenc_xenc_to_xy(wr, xi))
        bl = QPointF(*wenc_xenc_to_xy(wl, xi))

        poly = QPolygonF()
        poly.append(tl)
        poly.append(tr)
        poly.append(br)
        poly.append(bl)
        return poly

    def load_packet_image(self, defect: Defect, packet_image: PacketImage):
        """Overlay a packet image on its corresponding region."""
        pkt_id = defect.peak_packet_id

        pkt_meta = None
        for p in self._packet_raw_meta_array:
            if p.packet_id == pkt_id:
                pkt_meta = p
                break

        if pkt_meta is None:
            return

        data = packet_image.data
        if data is None or data.size == 0:
            return

        data_f = data.astype(np.float64)
        d_min, d_max = data_f.min(), data_f.max()
        if d_max > d_min:
            data_norm = (
                (data_f - d_min) / (d_max - d_min) * 255
            ).astype(np.uint8)
        else:
            data_norm = np.zeros_like(data_f, dtype=np.uint8)

        h, w = data_norm.shape
        bytes_per_line = w
        qimg = QImage(
            data_norm.data,
            w,
            h,
            bytes_per_line,
            QImage.Format.Format_Grayscale8,
        )

        wl, wr = pkt_meta.wenc_left, pkt_meta.wenc_right
        xo, xi = pkt_meta.xenc_outer, pkt_meta.xenc_inner

        tl = QPointF(*wenc_xenc_to_xy(wl, xo))
        tr = QPointF(*wenc_xenc_to_xy(wr, xo))
        bl = QPointF(*wenc_xenc_to_xy(wl, xi))
        br = QPointF(*wenc_xenc_to_xy(wr, xi))

        min_x = min(tl.x(), tr.x(), bl.x(), br.x())
        max_x = max(tl.x(), tr.x(), bl.x(), br.x())
        min_y = min(tl.y(), tr.y(), bl.y(), br.y())
        max_y = max(tl.y(), tr.y(), bl.y(), br.y())

        pixmap = QPixmap.fromImage(qimg)
        pixmap_item = self._scene.addPixmap(pixmap)
        pixmap_item.setZValue(6)

        target_rect = QRectF(min_x, min_y, max_x - min_x, max_y - min_y)
        pixmap_item.setPos(target_rect.topLeft())
        pixmap_item.setScale(target_rect.width() / w if w > 0 else 1.0)

        self._pixmap_items.append(pixmap_item)

    def _clear_image_overlays(self):
        for item in self._pixmap_items:
            self._scene.removeItem(item)
        self._pixmap_items.clear()

    def reset_view(self):
        """Clear all data and reset view."""
        self.clear_data_items()
        self._clear_image_overlays()
        for item in self._spiral_items:
            self._scene.removeItem(item)
        self._spiral_items.clear()
        self._defect_array = []
        self._event_array = []
        self._packet_raw_meta_array = []
        self._selected_item = None
        self.fit_circle()

    def drawForeground(self, painter: QPainter, rect: QRectF):
        """Draw center indicator when (0,0) is outside the viewport."""
        super().drawForeground(painter, rect)

        center = self.mapFromScene(0, 0)
        vp = self.viewport().rect()

        if vp.contains(center):
            return

        # intersection of viewport-center ray with viewport boundary
        vp_cx = vp.center().x()
        vp_cy = vp.center().y()
        dx = center.x() - vp_cx
        dy = center.y() - vp_cy

        if abs(dx) < 1 and abs(dy) < 1:
            return

        # parametric: intersect ray with each edge, pick closest positive t
        t_min = float("inf")
        for edge_x, edge_y, nx, ny in [
            (vp.left(), vp_cy, -1, 0),
            (vp.right(), vp_cy, 1, 0),
            (vp_cx, vp.top(), 0, -1),
            (vp_cx, vp.bottom(), 0, 1),
        ]:
            denom = dx * nx + dy * ny
            if abs(denom) < 1e-6:
                continue
            t = (nx * (edge_x - vp_cx) + ny * (edge_y - vp_cy)) / denom
            if t > 0 and t < t_min:
                t_min = t

        if t_min == float("inf"):
            return

        ex = vp_cx + dx * t_min
        ey = vp_cy + dy * t_min

        # direction unit vector toward center
        length = math.hypot(dx, dy)
        ux = dx / length
        uy = dy / length
        px = -uy
        py = ux

        # chevron < pointing toward center, offset inward to be fully visible
        inset = 14
        sx = ex - ux * inset
        sy = ey - uy * inset
        tip_x = sx + ux * 16
        tip_y = sy + uy * 16
        la_x = sx + px * 10
        la_y = sy + py * 10
        ra_x = sx - px * 10
        ra_y = sy - py * 10

        # draw chevron in viewport coords
        painter.save()
        painter.resetTransform()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        pen = QPen(QColor("#2563a0"), 2.8)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.drawLine(QPointF(tip_x, tip_y), QPointF(la_x, la_y))
        painter.drawLine(QPointF(tip_x, tip_y), QPointF(ra_x, ra_y))

        painter.restore()
