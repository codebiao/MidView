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
    QGraphicsItem,
    QMenu,
    QLabel,
    QRubberBand,
    QPushButton,
    QButtonGroup,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
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
        else:
            self._apply_style(self._color_normal, self._dot_radius)

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

    def __init__(self, event: Event, polygon: QPolygonF):
        super().__init__(polygon)
        self.event = event
        self.setAcceptHoverEvents(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.scene().views()[0].event_region_clicked.emit(self.event)
            event.accept()
            return
        super().mousePressEvent(event)


class EventInfoPanel(QWidget):
    """Floating panel showing event details with a close button."""

    closed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(
            "EventInfoPanel { background: rgba(250,250,248,240);"
            "border: 1px solid #c8c5c1; border-radius: 6px; }"
        )
        self.setFixedSize(320, 320)
        self.hide()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(2)

        # header row
        header = QWidget()
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(0, 0, 0, 0)

        title = QLabel("Event Info")
        title.setStyleSheet("font-weight: 700; font-size: 13px; color: #2a2a2a;")
        h_layout.addWidget(title)
        h_layout.addStretch()

        close_btn = QPushButton("×")
        close_btn.setFixedSize(20, 20)
        close_btn.setStyleSheet(
            "QPushButton { background: transparent; border: none;"
            "font-size: 16px; font-weight: 700; color: #999; }"
            "QPushButton:hover { color: #333; }"
        )
        close_btn.clicked.connect(self._on_close)
        h_layout.addWidget(close_btn)

        layout.addWidget(header)

        self._content = QLabel()
        self._content.setStyleSheet(
            "font-size: 12px; color: #3a3a3a; padding: 4px;"
            "background: rgba(0,0,0,0);"
        )
        self._content.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._content.setWordWrap(True)
        layout.addWidget(self._content)

    def show_event(self, event: Event):
        if hasattr(self, "_position"):
            self._position()
        lines = [
            f"this_ptr: {event.this_ptr}",
            f"parent: {event.parent}",
            f"next: {event.next}",
            f"prev: {event.prev}",
            f"next_track: {event.next_track}",
            f"prev_track: {event.prev_track}",
            f"track_root: {event.track_root}",
            f"count: {event.count}",
            f"track_count: {event.track_count}",
            f"track_node_count: {event.track_node_count}",
            f"status: {event.status}",
            f"track_id: {event.track_id}",
            f"event_id: {event.event_id}",
            f"proc_id: {event.proc_id}",
            f"packet_id: {event.packet_id}",
            f"peak_adc: {event.peak_adc:.1f}",
            f"peak_row: {event.peak_row:.1f}",
            f"peak_col: {event.peak_col:.1f}",
            f"x_encoder: {event.x_encoder:.1f}",
            f"w_encoder: {event.w_encoder:.1f}",
            f"radius: {event.radius:.1f}",
            f"theta: {event.theta:.4f}",
            f"x_cor: {event.x_cor:.1f}",
            f"y_cor: {event.y_cor:.1f}",
            f"x: {event.x:.1f}",
            f"y: {event.y:.1f}",
            f"snr: {event.snr:.1f}",
            f"ee: {event.ee:.6f}",
            f"ee_is_fitted: {event.ee_is_fitted}",
            f"xenc_merge_count: {event.xenc_merge_count:.1f}",
            f"wenc_merge_count: {event.wenc_merge_count:.1f}",
            f"wenc_per_um: {event.wenc_per_um:.3f}",
            f"box_width: {event.box_width:.1f}",
            f"box_height: {event.box_height:.1f}",
            f"xenc_outer: {event.xenc_outer:.1f}",
            f"xenc_inner: {event.xenc_inner:.1f}",
            f"wenc_left: {event.wenc_left:.1f}",
            f"wenc_right: {event.wenc_right:.1f}",
            f"acc_flag: {event.acc_flag}",
            f"cosmic_ray_flag: {event.cosmic_ray_flag}",
            f"saturated_flag: {event.saturated_flag}",
            f"pixel_sindex: {event.pixel_sindex}",
            f"pixel_eindex: {event.pixel_eindex}",
        ]
        self._content.setText("\n".join(lines))
        self.show()

    def _on_close(self):
        self.hide()
        self.closed.emit()


class CircularView(QGraphicsView):
    """Main circular visualization view."""

    defect_clicked = Signal(Defect)
    defect_context_requested = Signal(Defect)
    event_region_clicked = Signal(Event)

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
        self._spiral_item: QGraphicsPathItem | None = None
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

        self._mode = "pan"
        self._rubber_band: QRubberBand | None = None
        self._rubber_origin: QPointF | None = None

        self._setup_mode_bar()

        self._event_info = EventInfoPanel(self)

        def _position_event_panel():
            vp = self.viewport()
            if vp is not None:
                pw = self._event_info.width()
                self._event_info.move(vp.width() - pw - 2, 40)

        self._event_info._position = _position_event_panel
        self.event_region_clicked.connect(self._event_info.show_event)
        self.defect_clicked.connect(lambda d: self._event_info.hide())

    def _setup_mode_bar(self):
        btn_style = (
            "QPushButton { background: rgba(250,250,248,235); border: 1px solid #c8c5c1;"
            "border-radius: 4px; font-size: 15px; font-weight: 700; color: #555;"
            "font-family: 'Segoe UI Symbol', 'Segoe UI', sans-serif;"
            "min-width: 30px; min-height: 24px; padding: 0px; }"
            "QPushButton:checked { background: #cce0f5; border-color: #2563a0; color: #2563a0; }"
            "QPushButton:hover:!checked { background: rgba(224,222,219,240); }"
        )

        btn_w, btn_h = 34, 24

        self._home_btn = QPushButton("⌂", self)
        self._home_btn.setToolTip("Fit View")
        self._home_btn.setCheckable(True)
        self._home_btn.setFixedSize(btn_w, btn_h)
        self._home_btn.setStyleSheet(btn_style)
        self._home_btn.clicked.connect(self._on_mode_home)

        self._hand_btn = QPushButton("✋", self)
        self._hand_btn.setToolTip("Pan")
        self._hand_btn.setCheckable(True)
        self._hand_btn.setChecked(True)
        self._hand_btn.setFixedSize(btn_w, btn_h)
        self._hand_btn.setStyleSheet(btn_style)
        self._hand_btn.clicked.connect(self._on_mode_pan)

        self._zoom_btn = QPushButton("▭", self)
        self._zoom_btn.setToolTip("Zoom to Rectangle")
        self._zoom_btn.setCheckable(True)
        self._zoom_btn.setFixedSize(btn_w, btn_h)
        self._zoom_btn.setStyleSheet(btn_style)
        self._zoom_btn.clicked.connect(self._on_mode_zoom)

        self._mode_group = QButtonGroup(self)
        self._mode_group.setExclusive(True)
        self._mode_group.addButton(self._home_btn)
        self._mode_group.addButton(self._hand_btn)
        self._mode_group.addButton(self._zoom_btn)

        self._home_btn.move(8, 8)
        self._hand_btn.move(8 + btn_w + 2, 8)
        self._zoom_btn.move(8 + (btn_w + 2) * 2, 8)

    def _on_mode_home(self):
        self.fit_circle()
        self._update_scale_bar()
        self._hand_btn.setChecked(True)
        self.set_mode("pan")

    def _on_mode_pan(self):
        self.set_mode("pan")

    def _on_mode_zoom(self):
        self.set_mode("zoom_rect")

    def showEvent(self, event):
        super().showEvent(event)
        self.fit_circle()
        self._update_scale_bar()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.fit_circle()
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

    def draw_spiral_from_packets(self):
        """Draw spiral as connected line segments from packet endpoints."""
        if self._spiral_item:
            self._scene.removeItem(self._spiral_item)

        if not self._packet_raw_meta_array:
            return

        path = QPainterPath()
        first = True

        for pkt in self._packet_raw_meta_array:
            x_start, y_start = wenc_xenc_to_xy(
                pkt.wenc_left, pkt.xenc_outer
            )
            if first:
                path.moveTo(x_start, y_start)
                first = False
            else:
                path.lineTo(x_start, y_start)

            x_end, y_end = wenc_xenc_to_xy(pkt.wenc_right, pkt.xenc_inner)
            path.lineTo(x_end, y_end)

        pen = QPen(QColor("#c0c0c0"))
        pen.setCosmetic(True)
        pen.setWidthF(1.2)
        self._spiral_item = QGraphicsPathItem(path)
        self._spiral_item.setPen(pen)
        self._spiral_item.setZValue(1)
        self._scene.addItem(self._spiral_item)

    def load_data(
        self,
        defect_array: list[Defect],
        packet_raw_meta_array: list[PacketRawMeta],
    ):
        """Load and display defect and packet data. Events are lazy-loaded."""
        self._defect_array = defect_array
        self._event_array = []
        self._packet_raw_meta_array = packet_raw_meta_array

        self.clear_data_items()

        self.draw_spiral_from_packets()
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
                event.accept()
                return

            item = self._find_nearby_defect(scene_pos)
            if item is not None:
                if item is self._selected_item:
                    self._deselect_current()
                    self.defect_clicked.emit(None)
                else:
                    self.defect_clicked.emit(item.defect)
                event.accept()
                return

        elif event.button() == Qt.RightButton:
            if self._defect_items:
                scene_pos = self.mapToScene(event.pos())
                item = self._find_nearby_defect(scene_pos)
                if item is not None:
                    self._last_right_click_global = self.mapToGlobal(
                        event.pos()
                    )
                    self.defect_clicked.emit(item.defect)
                    self.defect_context_requested.emit(item.defect)
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
            self._mode == "zoom_rect"
            and self._rubber_band is not None
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
            event.button() == Qt.LeftButton
            and self._mode == "zoom_rect"
            and self._rubber_band is not None
            and self._rubber_origin is not None
        ):
            self._rubber_band.hide()
            rect = self._rubber_band.geometry()
            if rect.width() > 4 and rect.height() > 4:
                top_left = self.mapToScene(rect.topLeft())
                bottom_right = self.mapToScene(rect.bottomRight())
                scene_rect = QRectF(top_left, bottom_right)
                self.fitInView(
                    scene_rect, Qt.AspectRatioMode.KeepAspectRatio
                )
                self.scale(0.5, 0.5)
            self._rubber_origin = None
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
        menu = QMenu(self)
        clear_events = QAction("Clear All Events", self)
        clear_events.triggered.connect(self._clear_event_regions)
        menu.addAction(clear_events)

        clear_images = QAction("Clear All Packet Images", self)
        clear_images.triggered.connect(self._clear_image_overlays)
        menu.addAction(clear_images)

        menu.exec(event.globalPos())

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
        item.setZValue(6)
        self._scene.addItem(item)
        self._event_polygons.append(item)

        # 2. draw event chain regions as light blue solid rectangles
        root_idx = defect.event_root_index
        chain = get_event_chain(root_idx, event_array)

        event_pen = QPen(QColor("#5ba0d0"))
        event_pen.setCosmetic(True)
        event_pen.setWidthF(1.2)
        event_brush = QBrush(QColor(91, 160, 208, 50))

        for evt in chain:
            poly = self._make_region_polygon(
                evt.xenc_outer, evt.xenc_inner,
                evt.wenc_left, evt.wenc_right,
            )
            item = EventRegionItem(evt, poly)
            item.setPen(event_pen)
            item.setBrush(event_brush)
            item.setZValue(5)
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
        if self._spiral_item:
            self._scene.removeItem(self._spiral_item)
            self._spiral_item = None
        self._defect_array = []
        self._event_array = []
        self._packet_raw_meta_array = []
        self._selected_item = None
        self.fit_circle()
