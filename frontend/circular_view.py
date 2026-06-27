"""Circular wafer visualization widget using QGraphicsView."""

from __future__ import annotations

import math
import numpy as np
from PySide6.QtWidgets import (
    QGraphicsView,
    QGraphicsScene,
    QGraphicsEllipseItem,
    QGraphicsLineItem,
    QGraphicsPathItem,
    QGraphicsPixmapItem,
    QGraphicsRectItem,
    QGraphicsPolygonItem,
    QGraphicsSimpleTextItem,
    QGraphicsItem,
    QMenu,
    QLabel,
    QRubberBand,
)
from PySide6.QtCore import Qt, Signal, QPointF, QRectF, QLineF
from PySide6.QtGui import (
    QPainter,
    QPen,
    QColor,
    QBrush,
    QPainterPath,
    QPolygonF,
    QTransform,
    QFontMetricsF,
    QCursor,
    QImage,
    QPixmap,
    QAction,
    QFont,
)

from backend.models import Defect, Event, PacketRawMeta
from backend.data_load.event_loader import get_event_chain
from frontend.global_param import RADIUS_MAX, WENC_MAX
from frontend.xwenc_to_xy import xwenc_to_xy

NEARBY_SCREEN_PX = 25.0

class DefectItem(QGraphicsEllipseItem):
    """A defect data point with screen-constant size and selection support."""

    _dot_radius = 2.0
    _hover_radius = 4.0
    _select_radius = 6.0

    _color_normal = QColor("#dc3545")
    _color_hover = QColor("#ff8787")
    _color_select = QColor("#dc3545")

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

    _normal_pen = QPen(QColor("#9cc8e8"))
    _normal_pen.setCosmetic(True)
    _normal_pen.setWidthF(0.8)

    _select_pen = QPen(QColor("#6a9ac0"))
    _select_pen.setCosmetic(True)
    _select_pen.setWidthF(1.5)

    _normal_brush = QBrush(Qt.BrushStyle.NoBrush)
    _select_brush = QBrush(QColor(26, 90, 144, 35))

    _expand_pen = QPen(QColor(180, 180, 180, 100))
    _expand_pen.setCosmetic(True)
    _expand_pen.setWidthF(0.6)
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

        # flip Y so positive scene Y maps to visual top
        self.scale(1, -1)

        self._defect_items: dict[int, DefectItem] = {}
        self._event_polygons: list[QGraphicsPolygonItem] = []
        self._spiral_items: list[QGraphicsPathItem] = []
        self._packet_labels: list[QGraphicsSimpleTextItem] = []
        self._spiral_drawn: bool = False
        self._circle_item: QGraphicsEllipseItem | None = None
        self._packet8M_overlay_items: list[QGraphicsItem] = []
        self._selected_item: DefectItem | None = None
        self._rect_area_item: QGraphicsRectItem | None = None

        # measure distance state
        self._measure_mode = False
        self._measure_points: list[QPointF] = []
        self._measure_items: list[QGraphicsItem] = []
        self._measure_cursor: QCursor | None = None

        self._defect_array: list[Defect] = []
        self._event_array: list[Event] = []
        self._packet_raw_meta_array: list[PacketRawMeta] = []
        self._shown_event_defects: set[int] = set()
        self._defect_event_items: dict[int, list[QGraphicsPolygonItem]] = {}

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

        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)

        self._selected_event_item: EventRegionItem | None = None

    def _on_event_item_clicked(self, item: EventRegionItem):
        """Handle event region click — select, or deselect if already selected."""
        # clear previous dot
        if getattr(self, "_event_dot", None) is not None:
            self._scene.removeItem(self._event_dot)
            self._event_dot = None

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
            # draw blue dot at event position
            ex, ey = xwenc_to_xy(item.event.x_encoder, item.event.w_encoder)
            dot = QGraphicsEllipseItem(-4, -4, 8, 8)
            dot.setPos(ex, ey)
            dot.setPen(Qt.PenStyle.NoPen)
            dot.setBrush(QBrush(QColor("#9cc8e8")))
            dot.setZValue(550)
            dot.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations, True)
            self._scene.addItem(dot)
            self._event_dot = dot

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

        pen_a = QPen(QColor(160, 160, 160, 70))
        pen_a.setCosmetic(True); pen_a.setWidthF(1.2)
        pen_b = QPen(QColor(50, 50, 50, 70))
        pen_b.setCosmetic(True); pen_b.setWidthF(1.2)

        path_a = QPainterPath()
        path_b = QPainterPath()

        drawn = 0
        for seg_i, pkt in enumerate(packets):
            xs, ys = xwenc_to_xy(pkt.xenc_outer, pkt.wenc_left)
            xe, ye = xwenc_to_xy(pkt.xenc_inner, pkt.wenc_right)

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
            sx, sy = xwenc_to_xy(
                packets[0].xenc_outer, packets[0].wenc_left,
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
        _lfm = QFontMetricsF(label_font)
        _lh = _lfm.height()
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
            cx, cy = xwenc_to_xy(xc, wc)

            label = QGraphicsSimpleTextItem(str(pkt.packet_id))
            label.setFont(label_font)
            label.setBrush(label_color)
            label.setPos(cx, cy + _lh)
            label.setTransform(QTransform.fromScale(1, -1))
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
        self.fit_circle()

    def clear_data_items(self):
        """Remove all data-dependent items."""
        for item in self._defect_items.values():
            self._scene.removeItem(item)
        self._defect_items.clear()

        for item in self._event_polygons:
            self._scene.removeItem(item)
        self._event_polygons.clear()

        for item in self._packet8M_overlay_items:
            self._scene.removeItem(item)
        self._packet8M_overlay_items.clear()

        self._selected_item = None
        self._shown_event_defects.clear()
        self._defect_event_items.clear()
        for item in self._spiral_items:
            self._scene.removeItem(item)
        self._spiral_items.clear()
        for lbl in self._packet_labels:
            self._scene.removeItem(lbl)
        self._packet_labels.clear()
        self._packet_raw_meta_array = []
        self._event_array = []
        self._spiral_drawn = False

    def draw_defects(self):
        """Place defect points via (x_encoder, w_encoder) coordinate transform."""
        for defect in self._defect_array:
            x, y = xwenc_to_xy(defect.x_encoder, defect.w_encoder)
            item = DefectItem(defect)
            item.setPos(x, y)
            self._scene.addItem(item)
            self._defect_items[defect.index] = item

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
        if self._measure_mode and event.button() == Qt.LeftButton:
            scene_pos = self.mapToScene(event.pos())
            nearby = self._find_nearby_defect(scene_pos)
            if nearby is not None:
                scene_pos = nearby.scenePos()
            self._measure_points.append(scene_pos)
            if len(self._measure_points) == 1:
                # first point — show temporary dot
                dot = QGraphicsEllipseItem(-4, -4, 8, 8)
                dot.setPos(scene_pos)
                dot.setPen(Qt.PenStyle.NoPen)
                dot.setBrush(QBrush(QColor("#2563a0")))
                dot.setZValue(502)
                dot.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations, True)
                self._scene.addItem(dot)
                self._measure_items.append(dot)
            elif len(self._measure_points) == 2:
                self._draw_measurement(self._measure_points[0], self._measure_points[1])
                self._measure_mode = False
                self.viewport().setCursor(Qt.CursorShape.ArrowCursor)
                self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
            event.accept()
            return

        if event.button() == Qt.LeftButton:
            scene_pos = self.mapToScene(event.pos())

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

        clear_images = QAction("Clear All Packet8M", self)
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
        items: list[QGraphicsPolygonItem] = []
        self._defect_event_items[defect.index] = items

        # 1. draw defect's own region as red dashed rectangle
        defect_pen = QPen(QColor("#c0707a"))
        defect_pen.setCosmetic(True)
        defect_pen.setWidthF(1.0)
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
        items.append(item)

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
            items.append(item)

    def clear_defect_events(self, defect_index: int):
        """Clear events for a single defect."""
        items = self._defect_event_items.pop(defect_index, None)
        if items:
            for item in items:
                self._scene.removeItem(item)
                if item in self._event_polygons:
                    self._event_polygons.remove(item)
        self._shown_event_defects.discard(defect_index)

    def show_defect_rect_area(self, defect: Defect):
        """Draw the defect's bounding rectangle from XY corner points, orange transparent fill."""
        self.clear_defect_rect_area()
        x1, y1 = xwenc_to_xy(defect.xenc_outer, defect.wenc_left)
        x2, y2 = xwenc_to_xy(defect.xenc_outer, defect.wenc_right)
        x3, y3 = xwenc_to_xy(defect.xenc_inner, defect.wenc_right)
        x4, y4 = xwenc_to_xy(defect.xenc_inner, defect.wenc_left)
        min_x = min(x1, x2, x3, x4)
        max_x = max(x1, x2, x3, x4)
        min_y = min(y1, y2, y3, y4)
        max_y = max(y1, y2, y3, y4)
        rect = QRectF(min_x, min_y, max_x - min_x, max_y - min_y)
        pen = QPen(QColor("#888888"))
        pen.setCosmetic(True)
        pen.setWidthF(1.5)
        pen.setStyle(Qt.PenStyle.SolidLine)
        brush = QBrush(QColor(128, 128, 128, 60))
        self._rect_area_item = QGraphicsRectItem(rect)
        self._rect_area_item.setPen(pen)
        self._rect_area_item.setBrush(brush)
        self._rect_area_item.setZValue(200)
        self._scene.addItem(self._rect_area_item)

        length = max_x - min_x
        width_val = max_y - min_y
        min_dim = min(length, width_val)
        font_size = max(1, int(min_dim / 20))

        dim_font = QFont("monospace")
        dim_font.setPointSizeF(max(1.0, min_dim / 20))
        label_bottom = QGraphicsSimpleTextItem(f"{length:.0f}μm")
        label_bottom.setFont(dim_font)
        label_bottom.setBrush(QBrush(QColor("#888888")))
        self._scene.addItem(label_bottom)
        _bw = label_bottom.boundingRect().width()
        _bh = label_bottom.boundingRect().height()
        label_bottom.setPos(min_x + (length - _bw) / 2, max_y + 4 + _bh)
        label_bottom.setTransform(QTransform.fromScale(1, -1))
        label_bottom.setZValue(200)

        label_right = QGraphicsSimpleTextItem(f"{width_val:.0f}μm")
        label_right.setFont(dim_font)
        label_right.setBrush(QBrush(QColor("#888888")))
        self._scene.addItem(label_right)
        _rw = label_right.boundingRect().width()
        _rh = label_right.boundingRect().height()
        label_right.setPos(max_x + 4, min_y + (width_val - _rh) / 2 + _rh)
        label_right.setTransform(QTransform.fromScale(1, -1))
        label_right.setZValue(200)
        self._rect_labels = [label_bottom, label_right]

    def clear_defect_rect_area(self):
        if self._rect_area_item is not None:
            self._scene.removeItem(self._rect_area_item)
            self._rect_area_item = None
        for lbl in getattr(self, '_rect_labels', []):
            self._scene.removeItem(lbl)
        self._rect_labels = []

    def _clear_event_regions(self):
        for item in self._event_polygons:
            self._scene.removeItem(item)
        self._event_polygons.clear()
        self._shown_event_defects.clear()
        self._defect_event_items.clear()

    @staticmethod
    def _make_region_polygon(xo: float, xi: float, wl: float, wr: float) -> QPolygonF:
        """Build a 4-corner polygon from xenc/wenc bounds."""
        tl = QPointF(*xwenc_to_xy(xo, wl))
        tr = QPointF(*xwenc_to_xy(xo, wr))
        br = QPointF(*xwenc_to_xy(xi, wr))
        bl = QPointF(*xwenc_to_xy(xi, wl))

        poly = QPolygonF()
        poly.append(tl)
        poly.append(tr)
        poly.append(br)
        poly.append(bl)
        return poly

    def draw_packet8M_overlay(
        self, pixmap: QPixmap, x1: float, y1: float, x2: float, y2: float
    ):
        """Draw a packet8M transposed image on the canvas.

        Length (along P1–P2) = P1–P2 segment length.
        Width (perpendicular) = row count × 0.7 μm.
        The P1–P2 line bisects the image rows.
        """
        seg_len = math.hypot(x2 - x1, y2 - y1)
        mid_x = (x1 + x2) / 2
        mid_y = (y1 + y2) / 2
        angle = math.degrees(math.atan2(y2 - y1, x2 - x1))

        pw, ph = pixmap.width(), pixmap.height()
        if pw > 0 and seg_len > 0:
            target_w = int(seg_len)
            target_h = int(ph * 0.7)
            pixmap = pixmap.scaled(
                target_w, target_h,
                Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            pw = pixmap.width()
            ph = pixmap.height()

        item = QGraphicsPixmapItem(pixmap)
        t = QTransform()
        t.translate(mid_x, mid_y)
        t.rotate(angle)
        t.scale(1, -1)
        t.translate(-pw / 2, -ph / 2)
        item.setTransform(t)
        item.setZValue(2)
        self._scene.addItem(item)
        self._packet8M_overlay_items.append(item)

    def _clear_image_overlays(self):
        for item in self._packet8M_overlay_items:
            self._scene.removeItem(item)
        self._packet8M_overlay_items.clear()

    def start_measure_distance(self):
        """Enter measure-distance mode."""
        self._measure_mode = True
        self._measure_points.clear()
        self._clear_measurement()
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.viewport().setCursor(QCursor(Qt.CursorShape.CrossCursor))

    def _clear_measurement(self):
        for item in self._measure_items:
            self._scene.removeItem(item)
        self._measure_items.clear()

    def _draw_measurement(self, p1: QPointF, p2: QPointF):
        import math
        self._clear_measurement()
        dist = math.hypot(p2.x() - p1.x(), p2.y() - p1.y())
        mid = QPointF((p1.x() + p2.x()) / 2, (p1.y() + p2.y()) / 2)

        # adaptive scale based on visible scene extent
        vr = self.mapToScene(self.viewport().rect()).boundingRect()
        visible_diag = math.hypot(vr.width(), vr.height())
        s = max(0.05, min(1.0, dist / max(visible_diag, 1.0)))
        line_w = 2.0 + 6.0 * s
        font_pt = max(8, int(8 + 12 * s))

        def _px_to_scene(px: float) -> float:
            p0 = self.mapToScene(0, 0)
            p1 = self.mapToScene(px, 0)
            return abs(p1.x() - p0.x())

        # point markers (ignore transforms = constant screen size, like DefectItem)
        dot_r = 4.0
        dot1 = QGraphicsEllipseItem(-dot_r, -dot_r, dot_r * 2, dot_r * 2)
        dot1.setPos(p1)
        dot1.setPen(Qt.PenStyle.NoPen)
        dot1.setBrush(QBrush(QColor("#2563a0")))
        dot1.setZValue(502)
        dot1.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations, True)
        self._scene.addItem(dot1)
        self._measure_items.append(dot1)

        dot2 = QGraphicsEllipseItem(-dot_r, -dot_r, dot_r * 2, dot_r * 2)
        dot2.setPos(p2)
        dot2.setPen(Qt.PenStyle.NoPen)
        dot2.setBrush(QBrush(QColor("#2563a0")))
        dot2.setZValue(502)
        dot2.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations, True)
        self._scene.addItem(dot2)
        self._measure_items.append(dot2)

        # arrow line (cosmetic pen = constant pixel width)
        arrow = QGraphicsLineItem(QLineF(p1, p2))
        arrow_pen = QPen(QColor("#2563a0"))
        arrow_pen.setCosmetic(True)
        arrow_pen.setWidthF(line_w)
        arrow_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        arrow.setPen(arrow_pen)
        arrow.setZValue(500)
        self._scene.addItem(arrow)
        self._measure_items.append(arrow)

        # arrowhead at p2 (ignore transforms for fixed pixel size)
        head_px = 14 + 20 * s
        angle = math.atan2(p2.y() - p1.y(), p2.x() - p1.x())
        hl = _px_to_scene(head_px)
        ax1 = p2.x() - hl * math.cos(angle - 0.4)
        ay1 = p2.y() - hl * math.sin(angle - 0.4)
        ax2 = p2.x() - hl * math.cos(angle + 0.4)
        ay2 = p2.y() - hl * math.sin(angle + 0.4)
        head = QGraphicsPolygonItem()
        head.setPolygon(QPolygonF([p2, QPointF(ax1, ay1), QPointF(ax2, ay2)]))
        head.setPen(Qt.PenStyle.NoPen)
        head.setBrush(QBrush(QColor("#2563a0")))
        head.setZValue(500)
        head.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations, True)
        self._scene.addItem(head)
        self._measure_items.append(head)

        # labels (ignore transforms = constant pixel size, upright)
        offset = _px_to_scene(8)
        label_font = QFont("monospace", font_pt, QFont.Weight.Bold)

        p1_label = QGraphicsSimpleTextItem(f"({p1.x():.0f}, {p1.y():.0f})")
        p1_label.setBrush(QColor("#2563a0"))
        p1_label.setFont(label_font)
        p1_label.setZValue(503)
        p1_label.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations, True)
        p1_label.setPos(p1.x() - _px_to_scene(p1_label.boundingRect().width()) - offset, p1.y() + offset)
        self._scene.addItem(p1_label)
        self._measure_items.append(p1_label)

        p2_label = QGraphicsSimpleTextItem(f"({p2.x():.0f}, {p2.y():.0f})")
        p2_label.setBrush(QColor("#2563a0"))
        p2_label.setFont(label_font)
        p2_label.setZValue(503)
        p2_label.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations, True)
        p2_label.setPos(p2.x() + offset, p2.y() + offset)
        self._scene.addItem(p2_label)
        self._measure_items.append(p2_label)

        # distance label at midpoint, centered above the line
        dist_text = f"{dist:,.0f} μm"
        mid_label = QGraphicsSimpleTextItem(dist_text)
        mid_label.setBrush(QColor("#2563a0"))
        mid_label.setFont(label_font)
        mid_label.setZValue(503)
        mid_label.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations, True)
        mid_tw = _px_to_scene(mid_label.boundingRect().width())
        mid_label.setPos(mid.x() - mid_tw / 2, mid.y() - offset)
        self._scene.addItem(mid_label)
        self._measure_items.append(mid_label)

    def drawForeground(self, painter: QPainter, rect: QRectF):
        """Draw legend and center indicator when (0,0) is outside the viewport."""
        super().drawForeground(painter, rect)

        vp = self.viewport().rect()

        # ── legend (always visible, top-right below coord display) ──
        painter.save()
        painter.resetTransform()
        legend_font = QFont("monospace", 9)
        painter.setFont(legend_font)
        fm = painter.fontMetrics()
        rect_w, rect_h = 32, 15
        gap = 5
        col_gap = 18
        right = vp.right() - 10
        base = 48 + fm.ascent()
        row_top = base - fm.ascent()
        ry = row_top + (fm.height() - rect_h) / 2.0

        # defect bbox
        label1 = "defect bbox"
        tw1 = fm.horizontalAdvance(label1)
        rx1 = right - rect_w
        tx1 = rx1 - gap - tw1
        painter.setPen(QColor("#c0707a"))
        painter.drawText(tx1, base, label1)
        painter.setPen(QPen(QColor("#c0707a"), 1.0, Qt.PenStyle.DashLine))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(QRectF(rx1, ry, rect_w, rect_h))

        # event bbox
        label2 = "event bbox"
        tw2 = fm.horizontalAdvance(label2)
        rx2 = tx1 - col_gap - rect_w
        tx2 = rx2 - gap - tw2
        painter.setPen(QColor("#9cc8e8"))
        painter.drawText(tx2, base, label2)
        painter.setPen(QPen(QColor("#9cc8e8"), 1.0))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(QRectF(rx2, ry, rect_w, rect_h))

        painter.restore()

        center = self.mapFromScene(0, 0)
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

        pen = QPen(QColor("#dc3545"), 3.5)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.drawLine(QPointF(tip_x, tip_y), QPointF(la_x, la_y))
        painter.drawLine(QPointF(tip_x, tip_y), QPointF(ra_x, ra_y))

        painter.restore()
