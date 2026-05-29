"""Packet8M viewer dialog with image display, histogram, and processing controls."""

from __future__ import annotations

import os

import numpy as np
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QFrame,
    QPushButton,
    QWidget,
    QGraphicsView,
    QGraphicsScene,
    QGraphicsPixmapItem,
    QGraphicsRectItem,
    QGraphicsItem,
    QSlider,
    QMenu,
    QRubberBand,
    QMessageBox,
    QFileDialog,
    QSizePolicy,
)
from PySide6.QtCore import Qt, QEvent, QRectF, QTimer, QPointF
from PySide6.QtGui import (
    QPixmap,
    QImage,
    QPainter,
    QPen,
    QBrush,
    QColor,
    QFont,
)

from backend.data_load.packet8M_loader import load_packet8M
from backend.data_load.event_loader import load_events
from backend.data_load.packet_raw_meta_loader import (
    load_packet_raw_meta,
    find_packet_meta,
)
from frontend.xwenc_to_xy import xwenc_to_xy


def show_packet8m_viewer(mw):
    """Load and display a packet8M .tt file with transposed image."""
    last_dir = getattr(mw, "_last_packet8M_dir", None) or mw._data_folder or os.getcwd()
    path, _ = QFileDialog.getOpenFileName(
        mw, "Select packet8M File",
        last_dir, "Packet8M Files (*.tt);;All (*.*)",
    )
    if not path:
        return
    mw._last_packet8M_dir = os.path.dirname(path)
    try:
        head, data, _enc, _lineinfo, footer = load_packet8M(path)
    except Exception as e:
        QMessageBox.critical(mw, "Load Error", str(e))
        return

    # transpose and normalize uint16 → uint8 for display
    transposed = data.T.copy()
    d_f = transposed.astype(np.float64)
    d_min, d_max = d_f.min(), d_f.max()
    if d_max > d_min:
        norm = ((d_f - d_min) / (d_max - d_min) * 255).astype(np.uint8)
    else:
        norm = np.zeros_like(d_f, dtype=np.uint8)

    h, w = norm.shape

    qimg = QImage(
        norm.tobytes(), w, h, w, QImage.Format.Format_Grayscale8
    )
    pixmap = QPixmap.fromImage(qimg)

    dialog = QDialog(mw)
    dialog.setWindowTitle(
        f"Packet8M — {os.path.basename(path)}"
    )
    dialog.setAttribute(Qt.WA_DeleteOnClose)
    dialog.setMinimumSize(400, 300)
    dialog_w = mw.width()
    dialog_h = mw.height() * 7 // 8
    dialog.resize(dialog_w, dialog_h)

    main_layout = QVBoxLayout(dialog)
    main_layout.setContentsMargins(4, 4, 4, 4)
    main_layout.setSpacing(4)

    # --- row: home + coord info ---
    info_right = QLabel("x=0, y=0, value=0")
    info_right.setStyleSheet(
        "padding:0px 4px; font-family:monospace; color:#555;"
    )

    top_row = QHBoxLayout()
    top_row.setContentsMargins(0, 0, 0, 0)

    # --- canvas (fills remaining space) ---
    scene = QGraphicsScene()
    gv = QGraphicsView(scene)
    gv.setMinimumSize(200, 200)
    gv.setFrameShape(QGraphicsView.Shape.NoFrame)
    gv.setStyleSheet(
        "background-color: #e8e8e8; border:1px solid #aaa;"
    )
    gv.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
    gv.setTransformationAnchor(
        QGraphicsView.ViewportAnchor.AnchorUnderMouse
    )
    gv.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
    gv.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    gv.viewport().setMouseTracking(True)

    pixmap_item = QGraphicsPixmapItem(pixmap)
    pixmap_item.setTransformationMode(
        Qt.TransformationMode.FastTransformation
    )
    scene.addItem(pixmap_item)
    scene.setSceneRect(QRectF(pixmap.rect()))

    def _zoom_to_fit():
        gv.fitInView(scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
        QTimer.singleShot(10, lambda: gv.fitInView(
            scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio))

    pkt_info = QLabel(
        f"packet_id: {head['packet_id']}, "
        f"valid_line={footer['valid_line']}, "
        f"valid_pixels={head['sensor_width']}, "
        f"line_info={head.get('line_info', 'N/A')}"
    )
    pkt_info.setStyleSheet(
        "padding:0px 4px; font-family:monospace; font-size:12px; color:#555;"
    )

    top_row.addWidget(pkt_info)
    top_row.addStretch()
    top_row.addWidget(info_right)

    # --- axis arrows (QWidget overlay on viewport, always fixed) ---
    class _ArrowOverlay(QWidget):
        def paintEvent(self, event):
            p = QPainter(self)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            pen = QPen(QColor("#dc3545"))
            pen.setWidthF(2.2)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.setPen(pen)
            ox, oy = 8, 8
            L = 100
            # x arrow (right)
            p.drawLine(ox, oy, ox + L, oy)
            p.drawLine(ox + L - 6, oy - 4, ox + L, oy)
            p.drawLine(ox + L - 6, oy + 4, ox + L, oy)
            # y arrow (down)
            p.drawLine(ox, oy, ox, oy + L)
            p.drawLine(ox - 4, oy + L - 6, ox, oy + L)
            p.drawLine(ox + 4, oy + L - 6, ox, oy + L)
            # X, Y labels
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(QColor("#dc3545")))
            font = QFont("Segoe UI", 8, QFont.Weight.Bold)
            p.setFont(font)
            p.drawText(QRectF(ox + 50, oy + 2, 20, 12), Qt.AlignmentFlag.AlignCenter, "X")
            p.drawText(QRectF(ox + 4, oy + 50, 20, 12), Qt.AlignmentFlag.AlignCenter, "Y")
            # axis names (pen + brush for text visibility)
            p.setPen(QPen(QColor("#dc3545")))
            p.setBrush(QBrush(QColor("#dc3545")))
            font1 = QFont("Segoe UI", 9)
            p.setFont(font1)
            mid = ox + L // 2
            pw_wenc = p.fontMetrics().horizontalAdvance("Wenc") + 4
            p.drawText(QRectF(ox + L + 4, 0, pw_wenc, 14), Qt.AlignmentFlag.AlignLeft, "Wenc")
            # Xenc — below Y arrowhead, close to left edge
            pw_xenc = p.fontMetrics().horizontalAdvance("Xenc") + 4
            p.drawText(QRectF(2, oy + L + 4, pw_xenc, 14),
                       Qt.AlignmentFlag.AlignLeft, "Xenc")
            # origin "0"
            font0 = QFont("Segoe UI", 8, QFont.Weight.Bold)
            p.setFont(font0)
            p.drawText(QRectF(ox + 2, oy + 2, 12, 12), Qt.AlignmentFlag.AlignCenter, "0")
            p.end()

    axes_overlay = _ArrowOverlay(gv)
    axes_overlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
    axes_overlay.setFixedSize(160, 160)
    axes_overlay.setStyleSheet("background: transparent;")
    axes_overlay.move(2, 2)
    axes_overlay.show()
    axes_overlay.raise_()

    # right-click context menu + rubber-band zoom
    _event_rect_items: list[QGraphicsItem] = []
    _event_rect_map: dict[QGraphicsItem, object] = {}  # Event objects
    _selected_rect_item: QGraphicsRectItem | None = None
    _select_brush = QBrush(QColor(26, 90, 144, 80))
    _rubber_band: QRubberBand | None = None
    _rubber_origin: QPointF | None = None
    _suppress_ctx_menu = False
    gv.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

    def _on_context_menu(pos):
        nonlocal _suppress_ctx_menu
        if _suppress_ctx_menu:
            _suppress_ctx_menu = False
            return
        menu = QMenu(gv)
        menu.addAction("Fit View", _zoom_to_fit)
        menu.addAction("View All Events", lambda: _view_all_events())
        menu.addAction("Draw", _on_draw)
        menu.addSeparator()
        menu.addAction("Clear All Events", lambda: _clear_all_events())
        menu.exec(gv.mapToGlobal(pos))
    gv.customContextMenuRequested.connect(_on_context_menu)

    def _show_event_info(evt):
        lines = [
            f"index: {evt.index}",
            f"this_ptr: {evt.this_ptr}",
            f"parent: {evt.parent}",
            f"next: {evt.next}",
            f"prev: {evt.prev}",
            f"next_track: {evt.next_track}",
            f"prev_track: {evt.prev_track}",
            f"track_root: {evt.track_root}",
            f"count: {evt.count}",
            f"track_count: {evt.track_count}",
            f"track_node_count: {evt.track_node_count}",
            f"status: {evt.status}",
            f"track_id: {evt.track_id}",
            f"event_id: {evt.event_id}",
            f"defect_id: {evt.defect_id}",
            f"proc_id: {evt.proc_id}",
            f"packet_id: {evt.packet_id}",
            f"peak_adc: {evt.peak_adc:.1f}",
            f"peak_row: {evt.peak_row:.1f}",
            f"peak_col: {evt.peak_col:.1f}",
            f"x_encoder: {evt.x_encoder:.1f}",
            f"w_encoder: {evt.w_encoder:.1f}",
            f"radius: {evt.radius:.1f}",
            f"theta: {evt.theta:.4f}",
            f"x_cor: {evt.x_cor:.1f}",
            f"y_cor: {evt.y_cor:.1f}",
            f"x: {evt.x:.1f}",
            f"y: {evt.y:.1f}",
            f"snr: {evt.snr:.1f}",
            f"ee: {evt.ee:.6f}",
            f"ee_is_fitted: {evt.ee_is_fitted}",
            f"xenc_merge_count: {evt.xenc_merge_count:.1f}",
            f"wenc_merge_count: {evt.wenc_merge_count:.1f}",
            f"wenc_per_um: {evt.wenc_per_um:.3f}",
            f"check_sum: {evt.check_sum}",
            f"box_x: {evt.box_x:.1f}",
            f"box_y: {evt.box_y:.1f}",
            f"box_width: {evt.box_width:.1f}",
            f"box_height: {evt.box_height:.1f}",
            f"compressed2_box_x: {evt.compressed2_box_x:.1f}",
            f"compressed2_box_y: {evt.compressed2_box_y:.1f}",
            f"compressed2_box_width: {evt.compressed2_box_width:.1f}",
            f"compressed2_box_height: {evt.compressed2_box_height:.1f}",
            f"xenc_outer: {evt.xenc_outer:.1f}",
            f"xenc_inner: {evt.xenc_inner:.1f}",
            f"wenc_left: {evt.wenc_left:.1f}",
            f"wenc_right: {evt.wenc_right:.1f}",
            f"acc_flag: {evt.acc_flag}",
            f"cosmic_ray_flag: {evt.cosmic_ray_flag}",
            f"saturated_flag: {evt.saturated_flag}",
            f"pixel_sindex: {evt.pixel_sindex}",
            f"pixel_eindex: {evt.pixel_eindex}",
        ]
        evt_info_panel.setText("\n".join(lines))
        evt_info_panel.setAlignment(Qt.AlignTop)
        evt_info_panel.setStyleSheet(
            "padding:4px 8px; font-family:monospace; font-size:12px;"
            "color:#555; background:#f0f0ff; border:1px solid #aac;"
        )

    def _clear_event_info():
        nonlocal _selected_rect_item
        if _selected_rect_item is not None:
            _selected_rect_item.setBrush(Qt.BrushStyle.NoBrush)
            _selected_rect_item = None
        evt_info_panel.setText("Click an event box\nto view details")
        evt_info_panel.setAlignment(Qt.AlignCenter)
        evt_info_panel.setStyleSheet(
            "padding:4px 8px; font-family:monospace; font-size:12px;"
            "color:#888; background:#f0f0f0;"
        )

    def _clear_all_events():
        nonlocal _selected_rect_item
        for item in _event_rect_items:
            scene.removeItem(item)
        _event_rect_items.clear()
        _event_rect_map.clear()
        _selected_rect_item = None
        evt_info_panel.setText("Click an event box\nto view details")
        evt_info_panel.setAlignment(Qt.AlignCenter)
        evt_info_panel.setStyleSheet(
            "padding:4px 8px; font-family:monospace; font-size:12px;"
            "color:#888; background:#f0f0f0;"
        )

    def _view_all_events():
        for item in _event_rect_items:
            scene.removeItem(item)
        _event_rect_items.clear()
        pkt_id = head["packet_id"]
        if not mw._data_folder:
            QMessageBox.warning(
                dialog, "No Data", "Load data first.",
            )
            return
        if not mw._event_array:
            try:
                mw._event_array = load_events(mw._data_folder)
                mw.set_status("events", True, len(mw._event_array))
            except Exception:
                QMessageBox.warning(
                    dialog, "No Events",
                    "No events.csv found in the loaded data folder.",
                )
                return
        pen = QPen(QColor("#5da0d0"))
        pen.setCosmetic(True)
        pen.setWidthF(1.0)
        pen.setStyle(Qt.PenStyle.DashLine)
        # collect events for this packet, grouped by defect_id
        groups: dict[int, list] = {}
        for evt in mw._event_array:
            if evt.packet_id == pkt_id:
                groups.setdefault(evt.defect_id, []).append(evt)
                # box coords: original pixels → transposed (1:1 native)
                bx = evt.box_y
                by = evt.box_x
                bw = evt.box_height
                bh = evt.box_width
                rect_item = QGraphicsRectItem(bx, by, bw, bh)
                rect_item.setPen(pen)
                rect_item.setBrush(Qt.BrushStyle.NoBrush)
                rect_item.setZValue(100)
                rect_item.setAcceptedMouseButtons(Qt.MouseButton.LeftButton)
                rect_item.setCursor(Qt.CursorShape.PointingHandCursor)
                scene.addItem(rect_item)
                _event_rect_items.append(rect_item)
                _event_rect_map[rect_item] = evt
                # peak pixel (original peak_row→x, peak_col→y)
                px = evt.peak_row
                py = evt.peak_col
                dot = QGraphicsRectItem(px, py, 1, 1)
                dot.setPen(Qt.PenStyle.NoPen)
                dot.setBrush(QBrush(QColor("#d4646e")))
                dot.setZValue(101)
                scene.addItem(dot)
                _event_rect_items.append(dot)

        # merged defect-level red dashed bboxes
        defect_pen = QPen(QColor("#d4646e"))
        defect_pen.setCosmetic(True)
        defect_pen.setWidthF(1.0)
        defect_pen.setStyle(Qt.PenStyle.DashLine)
        for defect_id, evts in groups.items():
            if defect_id < 0:
                continue
            min_x = min(e.box_y for e in evts)
            min_y = min(e.box_x for e in evts)
            max_x = max(e.box_y + e.box_height for e in evts)
            max_y = max(e.box_x + e.box_width for e in evts)
            merged_rect = QGraphicsRectItem(
                min_x, min_y, max_x - min_x, max_y - min_y
            )
            merged_rect.setPen(defect_pen)
            merged_rect.setBrush(Qt.BrushStyle.NoBrush)
            merged_rect.setZValue(102)
            merged_rect.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
            scene.addItem(merged_rect)
            _event_rect_items.append(merged_rect)

    # --- left column: canvas + path ---
    left_col = QVBoxLayout()
    top_bar = QWidget()
    top_bar.setLayout(top_row)

    left_col.setContentsMargins(0, 0, 0, 0)
    left_col.setSpacing(2)
    left_col.addWidget(top_bar)
    left_col.addWidget(gv)

    # --- right column: event info ---
    evt_right = QVBoxLayout()
    evt_right.setContentsMargins(0, 0, 0, 0)
    evt_right.setSpacing(0)

    evt_title = QLabel("Event Info")
    evt_title.setStyleSheet(
        "background-color: #d8d6d2; padding:4px 8px;"
        "font-size:13px; font-weight:700; color:#333;"
    )
    evt_right.addWidget(evt_title)

    evt_info_panel = QLabel("Click an event box\nto view details")
    evt_info_panel.setStyleSheet(
        "padding:4px 8px; font-family:monospace; font-size:12px;"
        "color:#888; background:#f0f0f0;"
    )
    evt_info_panel.setAlignment(Qt.AlignCenter)
    evt_info_panel.setWordWrap(True)
    evt_info_scroll = QScrollArea()
    evt_info_scroll.setWidgetResizable(True)
    evt_info_scroll.setFixedWidth(270)
    evt_info_scroll.setFrameShape(QFrame.Shape.NoFrame)
    evt_info_scroll.setWidget(evt_info_panel)
    evt_right.addWidget(evt_info_scroll)

    # --- body: left + right ---
    body = QHBoxLayout()
    body.setSpacing(0)
    body.addLayout(left_col)
    body.addLayout(evt_right)
    main_layout.addLayout(body)

    # --- bottom row: processing ---
    bottom_row = QHBoxLayout()
    bottom_row.setSpacing(8)

    # processing panel
    src_data = transposed.copy()

    proc_group = QFrame()
    proc_group.setFixedHeight(230)
    proc_group.setMaximumWidth(250)
    proc_group.setStyleSheet(
        "QFrame { background:transparent; border:1px solid #ddd; border-radius:4px; }"
    )
    proc_layout = QVBoxLayout(proc_group)
    proc_layout.setContentsMargins(6, 4, 6, 4)
    proc_layout.setSpacing(2)

    proc_layout.addWidget(QLabel("<b>Processing</b>"))

    d_min_proc = int(src_data.min())
    d_max_proc = int(src_data.max())

    # histogram — red, adaptive width
    hist_w, hist_h = 230, 50
    hist_pm = QPixmap(hist_w, hist_h)
    hist_pm.fill(Qt.GlobalColor.transparent)
    hp = QPainter(hist_pm)
    flat = src_data.ravel()
    bins = min(80, max(10, len(flat) // 100))
    cnts, _e = np.histogram(flat, bins=bins)
    cnts = cnts.astype(np.float64)
    mx = cnts.max()
    if mx > 0:
        cnts = cnts / mx * (hist_h - 4)
    bw = (hist_w - 4) / len(cnts)
    hp.setPen(Qt.PenStyle.NoPen)
    hp.setBrush(QBrush(QColor("#dc3545")))
    for i, c in enumerate(cnts):
        hp.drawRect(QRectF(2 + i * bw, hist_h - 2 - max(1, int(c)), bw - 1, max(1, int(c))))
    hp.end()
    hist_lbl = QLabel()
    hist_lbl.setPixmap(hist_pm)
    hist_lbl.setScaledContents(True)
    hist_lbl.setMinimumHeight(50)
    hist_lbl.setSizePolicy(
        QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
    )
    proc_layout.addWidget(hist_lbl, 1)

    hl = QHBoxLayout()
    hl.setContentsMargins(2, 0, 2, 0)
    lbl_hmin = QLabel(str(d_min))
    lbl_hmin.setStyleSheet("font-family:monospace; font-size:9px; color:#888;")
    lbl_hmax = QLabel(str(d_max))
    lbl_hmax.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
    lbl_hmax.setStyleSheet("font-family:monospace; font-size:9px; color:#888;")
    hl.addWidget(lbl_hmin)
    hl.addWidget(lbl_hmax)
    proc_layout.addLayout(hl)

    def _slider_row(label, rmin, rmax, default):
        row = QHBoxLayout()
        lbl = QLabel(label + ":")
        lbl.setFixedWidth(36)
        row.addWidget(lbl)
        btn_m = QPushButton("−")
        btn_m.setFixedSize(18, 18)
        btn_m.setStyleSheet("padding:0px; font-size:11px;")
        row.addWidget(btn_m)
        sl = QSlider(Qt.Orientation.Horizontal)
        sl.setRange(rmin, rmax)
        sl.setValue(default)
        row.addWidget(sl)
        btn_p = QPushButton("+")
        btn_p.setFixedSize(18, 18)
        btn_p.setStyleSheet("padding:0px; font-size:11px;")
        row.addWidget(btn_p)
        val = QLabel(str(default))
        val.setFixedWidth(36)
        val.setStyleSheet("font-family:monospace; font-size:10px;")
        row.addWidget(val)
        btn_m.clicked.connect(lambda: sl.setValue(sl.value() - 1))
        btn_p.clicked.connect(lambda: sl.setValue(sl.value() + 1))
        return row, sl, val

    sl_range = max(1, d_max_proc - d_min_proc)

    min_row, min_sl, min_val = _slider_row("Min", 0, sl_range, 0)
    proc_layout.addLayout(min_row)

    max_row, max_sl, max_val = _slider_row("Max", 0, sl_range, sl_range)
    proc_layout.addLayout(max_row)

    ctr_row, ctr_sl, ctr_val = _slider_row("Ctr", 10, 300, 100)
    proc_layout.addLayout(ctr_row)

    brt_row, brt_sl, brt_val = _slider_row("Brt", -100, 100, 0)
    proc_layout.addLayout(brt_row)

    btn_row = QHBoxLayout()
    btn_style = "QPushButton { padding:1px 0px; font-size:11px; min-height:20px; }"
    auto_btn = QPushButton("Auto")
    auto_btn.setStyleSheet(btn_style)
    reset_btn = QPushButton("Reset")
    reset_btn.setStyleSheet(btn_style)

    def _on_draw():
        if not mw._data_folder:
            QMessageBox.warning(
                dialog, "No Data", "Load data first.",
            )
            return
        if not mw._packet_raw_meta_array:
            try:
                mw._packet_raw_meta_array = load_packet_raw_meta(
                    mw._data_folder
                )
                mw.set_status(
                    "packet_meta", True, len(mw._packet_raw_meta_array)
                )
            except Exception:
                QMessageBox.warning(
                    dialog, "No Packet Meta",
                    "No packet_raw_meta.csv found in the loaded data folder.",
                )
                return
        pkt_id = head["packet_id"]
        d_f2 = transposed.astype(np.float64)
        lo, hi = _get_min_max()
        d_f2 = np.clip(d_f2, lo, hi)
        if hi > lo:
            norm2 = ((d_f2 - lo) / (hi - lo) * 255).astype(np.uint8)
        else:
            norm2 = np.zeros_like(d_f2, dtype=np.uint8)
        c = ctr_sl.value() / 100.0
        b = brt_sl.value()
        norm2 = np.clip(norm2 * c + b, 0, 255).astype(np.uint8)
        th2, tw2 = norm2.shape
        qimg2 = QImage(norm2.tobytes(), tw2, th2, tw2, QImage.Format.Format_Grayscale8)
        pixmap2 = QPixmap.fromImage(qimg2)

        pkt_meta = find_packet_meta(pkt_id, mw._packet_raw_meta_array)
        if pkt_meta is not None:
            x1, y1 = xwenc_to_xy(pkt_meta.xenc_outer, pkt_meta.wenc_left)
            x2, y2 = xwenc_to_xy(pkt_meta.xenc_inner, pkt_meta.wenc_right)
            mw._circular_view.draw_packet8M_overlay(pixmap2, x1, y1, x2, y2)
            mw._circular_view.centerOn((x1 + x2) / 2, (y1 + y2) / 2)
        else:
            QMessageBox.warning(
                dialog, "Not Found",
                f"Packet #{pkt_id} not found in packetMeta.",
            )

    btn_row.addWidget(auto_btn)
    btn_row.addWidget(reset_btn)
    proc_layout.addLayout(btn_row)

    def _get_min_max():
        lo = d_min_proc + min_sl.value()
        hi = d_min_proc + max_sl.value()
        if hi <= lo:
            hi = lo + 1
        return lo, hi

    def _refresh_pixmap():
        lo, hi = _get_min_max()
        c = ctr_sl.value() / 100.0
        b = brt_sl.value()

        d_f2 = transposed.astype(np.float64)
        d_f2 = np.clip(d_f2, lo, hi)
        if hi > lo:
            n = ((d_f2 - lo) / (hi - lo) * 255).astype(np.uint8)
        else:
            n = np.zeros_like(d_f2, dtype=np.uint8)
        n = np.clip(n * c + b, 0, 255).astype(np.uint8)

        qimg2 = QImage(
            n.tobytes(), w, h, w, QImage.Format.Format_Grayscale8
        )
        pixmap_item.setPixmap(QPixmap.fromImage(qimg2))
        # update labels
        lo, hi = _get_min_max()
        min_val.setText(str(lo))
        max_val.setText(str(hi))
        ctr_val.setText(str(ctr_sl.value()))
        brt_val.setText(str(brt_sl.value()))
        lbl_hmin.setText(str(lo))
        lbl_hmax.setText(str(hi))

        # redraw histogram for [lo, hi] range
        masked = src_data[(src_data >= lo) & (src_data <= hi)]
        if len(masked) == 0:
            masked = np.array([lo])
        cnts2, _ = np.histogram(masked, bins=bins)
        cnts2 = cnts2.astype(np.float64)
        mx2 = cnts2.max()
        if mx2 > 0:
            cnts2 = cnts2 / mx2 * (hist_h - 4)
        hist_pm2 = QPixmap(hist_w, hist_h)
        hist_pm2.fill(Qt.GlobalColor.transparent)
        hp2 = QPainter(hist_pm2)
        hp2.setPen(Qt.PenStyle.NoPen)
        hp2.setBrush(QBrush(QColor("#dc3545")))
        for i2, c2 in enumerate(cnts2):
            hp2.drawRect(QRectF(2 + i2 * bw, hist_h - 2 - max(1, int(c2)), bw - 1, max(1, int(c2))))
        hp2.end()
        hist_lbl.setPixmap(hist_pm2)

    def _auto_adjust():
        flat2 = src_data.ravel()
        new_lo = int(np.percentile(flat2, 0.5))
        new_hi = int(np.percentile(flat2, 99.5))
        if new_hi <= new_lo:
            new_lo, new_hi = d_min_proc, d_max_proc
        min_sl.setValue(max(0, new_lo - d_min_proc))
        max_sl.setValue(min(sl_range, new_hi - d_min_proc))
        ctr_sl.setValue(100)
        brt_sl.setValue(0)
        _refresh_pixmap()

    def _reset():
        min_sl.setValue(0)
        max_sl.setValue(sl_range)
        ctr_sl.setValue(100)
        brt_sl.setValue(0)
        _refresh_pixmap()

    min_sl.valueChanged.connect(_refresh_pixmap)
    max_sl.valueChanged.connect(_refresh_pixmap)
    ctr_sl.valueChanged.connect(_refresh_pixmap)
    brt_sl.valueChanged.connect(_refresh_pixmap)
    auto_btn.clicked.connect(_auto_adjust)
    reset_btn.clicked.connect(_reset)

    _refresh_pixmap()

    # pixel tracking (1:1 native resolution)
    display_bit_depth = 16

    def _pkt_filter(obj, event):
        if event.type() == QEvent.Type.MouseButtonPress:
            if event.button() == Qt.MouseButton.RightButton:
                nonlocal _rubber_band, _rubber_origin
                _rubber_origin = event.pos()
                if _rubber_band is None:
                    _rubber_band = QRubberBand(
                        QRubberBand.Shape.Rectangle, gv
                    )
                _rubber_band.setGeometry(
                    event.pos().x(), event.pos().y(), 0, 0
                )
                _rubber_band.show()
                return True
            elif event.button() == Qt.MouseButton.LeftButton:
                sp = gv.mapToScene(event.pos())
                for rect_item, evt in _event_rect_map.items():
                    if rect_item.contains(sp):
                        nonlocal _selected_rect_item
                        if _selected_rect_item is not None:
                            _selected_rect_item.setBrush(Qt.BrushStyle.NoBrush)
                        if _selected_rect_item is rect_item:
                            _selected_rect_item = None
                        else:
                            _selected_rect_item = rect_item
                            rect_item.setBrush(_select_brush)
                            _show_event_info(evt)
                        return True
        elif event.type() == QEvent.Type.MouseMove:
            if _rubber_band is not None and _rubber_origin is not None:
                x = min(_rubber_origin.x(), event.pos().x())
                y = min(_rubber_origin.y(), event.pos().y())
                w_rb = abs(event.pos().x() - _rubber_origin.x())
                h_rb = abs(event.pos().y() - _rubber_origin.y())
                _rubber_band.setGeometry(x, y, w_rb, h_rb)
                return True
            sp = gv.mapToScene(event.pos())
            ix, iy = int(sp.x()), int(sp.y())
            if 0 <= ix < w and 0 <= iy < h:
                val = int(transposed[iy, ix])
                if display_bit_depth == 8:
                    val = val >> 8
                info_right.setText(f"x={ix}, y={iy}, value={val}")
            else:
                info_right.setText("x=0, y=0, value=0")
        elif event.type() == QEvent.Type.MouseButtonRelease:
            if event.button() == Qt.MouseButton.RightButton:
                if _rubber_band is not None:
                    _rubber_band.hide()
                    rect = _rubber_band.geometry()
                    _rubber_origin = None
                    if rect.width() > 4 and rect.height() > 4:
                        nonlocal _suppress_ctx_menu
                        _suppress_ctx_menu = True
                        top_left = gv.mapToScene(rect.topLeft())
                        bottom_right = gv.mapToScene(rect.bottomRight())
                        scene_rect = QRectF(top_left, bottom_right)
                        gv.fitInView(
                            scene_rect,
                            Qt.AspectRatioMode.KeepAspectRatio,
                        )
                return False
        elif event.type() == QEvent.Type.Leave:
            info_right.setText("x=0, y=0, value=0")
        elif event.type() == QEvent.Type.Wheel:
            delta = event.angleDelta().y()
            factor = 1.25 if delta > 0 else 0.8
            gv.scale(factor, factor)
            return True
        return False

    gv.viewport().installEventFilter(mw)
    if not hasattr(mw, "_dialog_filters"):
        mw._dialog_filters = {}
        _orig = mw.eventFilter

        def _global_filter(obj, event):
            cb = mw._dialog_filters.get(obj)
            if cb:
                return cb(obj, event)
            if _orig:
                return _orig(obj, event)
            return False

        mw.eventFilter = _global_filter

    mw._dialog_filters[gv.viewport()] = _pkt_filter

    bottom_row.addWidget(proc_group)

    # processing action buttons
    btn_col = QVBoxLayout()
    btn_col.setSpacing(4)

    def _on_dehaze():
        pass

    def _on_conv2():
        pass

    dehaze_btn = QPushButton("Dehaze")
    dehaze_btn.setStyleSheet(btn_style)
    dehaze_btn.clicked.connect(_on_dehaze)
    btn_col.addWidget(dehaze_btn)

    conv2_btn = QPushButton("Conv2×2")
    conv2_btn.setStyleSheet(btn_style)
    conv2_btn.clicked.connect(_on_conv2)
    btn_col.addWidget(conv2_btn)

    bottom_row.addLayout(btn_col)
    bottom_row.addStretch()
    main_layout.addLayout(bottom_row)

    dialog.resize(dialog_w, dialog_h)
    RIGHT_W = 300

    def _sync_width():
        if w <= 0 or h <= 0:
            return
        cw = max(dialog.width() - RIGHT_W, 200)
        gv.setFixedWidth(cw)
        top_bar.setFixedWidth(cw)

    dialog.installEventFilter(mw)
    mw._dialog_filters[dialog] = lambda obj, event: (
        _sync_width() or False
        if event.type() == QEvent.Type.Resize else False
    )

    dialog.show()
    vh = gv.height()
    if vh > 0 and h > 0 and w > 0:
        vw_new = int(vh * w / h)
        gv.setFixedWidth(vw_new)
        top_bar.setFixedWidth(vw_new)
        dialog.resize(vw_new + RIGHT_W, dialog.height())
    QTimer.singleShot(0, _zoom_to_fit)
