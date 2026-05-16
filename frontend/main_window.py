"""Main application window for MidView."""

from __future__ import annotations

import math
import os
import subprocess
from PySide6.QtWidgets import (
    QMainWindow,
    QToolBar,
    QStatusBar,
    QSplitter,
    QFileDialog,
    QMessageBox,
    QMenu,
    QDialog,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QGraphicsView,
    QGraphicsScene,
    QGraphicsPixmapItem,
    QGraphicsRectItem,
    QFrame,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QAbstractScrollArea,
    QComboBox,
    QSizePolicy,
    QLayout,
    QApplication,
    QSlider,
)
from PySide6.QtCore import Qt, QSize, Signal, QEvent, QRectF, QTimer
from PySide6.QtGui import QAction, QCursor, QPixmap, QImage, QPainter, QPen, QBrush, QColor

from frontend.circular_view import CircularView, wenc_xenc_to_xy
from frontend.detail_panel import DetailPanel
from frontend.theme import LIGHT_THEME
from backend.models import Defect, Event, PacketRawMeta, PacketImage, ImageMeta
from backend.data_load.defect_loader import load_defects
from backend.data_load.event_loader import load_events, get_event_chain
from backend.data_load.packet_raw_meta_loader import (
    load_packet_raw_meta,
    find_packet_meta,
)
from backend.data_load.image_meta_loader import load_image_meta
from backend.data_load.packet8M_loader import load_packet8M
import numpy as np


class EventInfoPanel(QWidget):
    """Panel showing event details, positioned in the right column."""

    closed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(300)
        self.setMaximumWidth(420)
        self.setStyleSheet(
            "EventInfoPanel { background-color: #dce8f5; }"
        )
        self.hide()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # header
        header = QWidget()
        header.setStyleSheet("background-color: #b8cfe0;")
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(8, 4, 4, 4)

        title = QLabel("Event Info")
        title.setObjectName("sectionTitle")
        title.setStyleSheet("background: transparent;")
        h_layout.addWidget(title)
        h_layout.addStretch()

        close_btn = QPushButton("×")
        close_btn.setFixedSize(20, 20)
        close_btn.setStyleSheet(
            "QPushButton { background: transparent; border: none;"
            "font-size: 16px; font-weight: 700; color: #557799; }"
            "QPushButton:hover { color: #334455; }"
        )
        close_btn.clicked.connect(self._on_close)
        h_layout.addWidget(close_btn)

        layout.addWidget(header)

        # scrollable content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background-color: #e8f0f8;")
        scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        self._content = QLabel()
        self._content.setStyleSheet(
            "font-size: 12px; color: #3a3a3a; padding: 4px;"
            "background: transparent;"
        )
        self._content.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._content.setWordWrap(True)
        scroll.setWidget(self._content)
        layout.addWidget(scroll)

    def show_event(self, event: Event):
        if event is None:
            self.hide()
            return
        lines = [
            f"index: {event.index}",
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


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MidView — Wafer Defect Visualization")
        self.resize(1600, 1000)
        self.setMinimumSize(1000, 600)
        self.setStyleSheet(LIGHT_THEME)

        self._data_folder: str | None = None
        self._defect_array: list[Defect] = []
        self._event_array: list[Event] = []
        self._packet_raw_meta_array: list[PacketRawMeta] = []
        self._img_meta_array: list[ImageMeta] = []

        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(2)

        self._circular_view = CircularView()

        # status bar above canvas (left side only)
        self._status_frame = QFrame()
        self._status_frame.setStyleSheet(
            "QFrame { background: #e8e6e3; border-bottom: 1px solid #ccc; }"
        )
        status_layout = QHBoxLayout(self._status_frame)
        status_layout.setContentsMargins(8, 3, 8, 3)
        status_layout.setSpacing(10)

        self._status_labels: dict[str, QLabel] = {}
        for key, label_text in [
            ("defect", "Defects"),
            ("events", "Events"),
            ("packet_meta", "PacketMeta"),
            ("img_meta", "ImgMeta"),
        ]:
            lbl = QLabel(f"{label_text}: 0")
            lbl.setStyleSheet(
                "background: #d8d6d2; color: #888; padding: 2px 10px;"
                "border-radius: 3px; font-size: 11px; font-family: monospace;"
            )
            status_layout.addWidget(lbl)
            self._status_labels[key] = lbl

        self._status_path = QPushButton("")
        self._status_path.setFlat(True)
        self._status_path.setCursor(Qt.CursorShape.PointingHandCursor)
        self._status_path.setStyleSheet(
            "QPushButton { color: #666; font-size: 11px; font-family: monospace; "
            "text-align: left; padding: 0px; border: none; background: transparent; }"
            "QPushButton:hover { color: #2563a0; text-decoration: underline; }"
        )
        self._status_path.clicked.connect(self._on_path_clicked)
        status_layout.addWidget(self._status_path)
        status_layout.addStretch()

        # left side: status bar + canvas
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)
        left_layout.addWidget(self._status_frame)
        left_layout.addWidget(self._circular_view)

        # right column: detail panel + event info panel
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        self._detail_panel = DetailPanel()
        self._event_info_panel = EventInfoPanel()

        right_layout.addWidget(self._detail_panel)
        right_layout.addWidget(self._event_info_panel)

        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)

        self.setCentralWidget(splitter)

        toolbar = QToolBar("Main")
        toolbar.setIconSize(QSize(20, 20))
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        self._load_action = QAction("Load Data", self)
        self._load_action.triggered.connect(self._on_load_data)
        toolbar.addAction(self._load_action)

        # Analysis menu
        analysis_menu = QMenu("Analysis", self)
        coord_compare_action = QAction("坐标对比", self)
        coord_compare_action.triggered.connect(self._on_coord_compare)
        parse_pkt_action = QAction("Parse Packet8M", self)
        parse_pkt_action.triggered.connect(self._on_load_packet8M)
        analysis_menu.addAction(parse_pkt_action)

        analysis_menu.addAction(coord_compare_action)

        analysis_btn = QPushButton("Analysis")
        analysis_btn.setMenu(analysis_menu)
        analysis_btn.setStyleSheet(
            "QPushButton { padding: 3px 10px; font-size: 12px;"
            "text-align: center; }"
            "QPushButton::menu-indicator { image: none; }"
        )
        toolbar.addWidget(analysis_btn)

        load_pkt_action = QAction("Load Packet8M", self)
        load_pkt_action.triggered.connect(self._on_load_packet8M_toolbar)
        toolbar.addAction(load_pkt_action)

        self._status = QStatusBar()
        self.setStatusBar(self._status)
        self._status.showMessage("Ready — Click 'Load Data' to begin")

    def _connect_signals(self):
        self._circular_view.defect_clicked.connect(self._on_defect_clicked)
        self._circular_view.defect_context_requested.connect(
            self._on_defect_context_menu
        )
        self._detail_panel.search_requested.connect(self._on_search)
        self._circular_view.event_region_clicked.connect(
            self._event_info_panel.show_event
        )
        self._circular_view.view_all_events_requested.connect(
            self._on_view_all_events
        )
        self._circular_view.view_all_spiral_requested.connect(
            self._on_view_all_spiral
        )

    def set_status(self, key: str, loaded: bool, count: int = 0):
        """Update a data-status label."""
        lbl = self._status_labels.get(key)
        if lbl is None:
            return
        names = {
            "defect": "Defects", "events": "Events",
            "packet_meta": "PacketMeta", "img_meta": "ImgMeta",
        }
        name = names.get(key, key)
        if loaded:
            lbl.setText(f"{name}: {count}")
            lbl.setStyleSheet(
                "background: #cce5cc; color: #2a6e2a; padding: 2px 10px;"
                "border-radius: 3px; font-size: 11px; font-family: monospace;"
            )
        else:
            lbl.setText(f"{name}: 0")
            lbl.setStyleSheet(
                "background: #d8d6d2; color: #888; padding: 2px 10px;"
                "border-radius: 3px; font-size: 11px; font-family: monospace;"
            )

    def _on_path_clicked(self):
        """Open the data folder in file explorer."""
        if self._data_folder:
            path = os.path.normpath(self._data_folder)
            try:
                os.startfile(path)
            except OSError:
                subprocess.run(["explorer", path])

    def _on_search(self, field: str, value: str):
        if not self._defect_array:
            return

        match = None
        for d in self._defect_array:
            d_val = str(getattr(d, field, ""))
            if d_val == value:
                match = d
                break

        if match is None:
            self._status.showMessage(
                f"No defect found with {field}={value}"
            )
            return

        sx, sy = wenc_xenc_to_xy(match.w_encoder, match.x_encoder)
        self._circular_view.centerOn(sx, sy)
        self._on_defect_clicked(match)
        self._status.showMessage(
            f"Found defect #{match.defect_id} ({field}={value})"
        )

    def _on_load_data(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Select Data Folder", self._data_folder or os.getcwd()
        )
        if not folder:
            return

        try:
            self._status.showMessage(f"Loading data from {folder}...")
            self._defect_array = load_defects(folder)
            self._packet_raw_meta_array = []
            self._img_meta_array = []
            self._event_array = []

            self._data_folder = folder
            self._circular_view.load_data(
                self._defect_array,
                self._packet_raw_meta_array,
            )
            self.set_status("defect", True, len(self._defect_array))
            self.set_status("events", False)
            self.set_status("packet_meta", False)
            self.set_status("img_meta", False)
            self._status_path.setText(folder)

            n_defects = len(self._defect_array)
            self._status.showMessage(
                f"Loaded {n_defects} defects from {folder}"
            )
            self._detail_panel.clear()

        except Exception as e:
            QMessageBox.critical(self, "Load Error", str(e))
            self._status.showMessage("Load failed")

    def _on_defect_clicked(self, defect: Defect):
        if defect is None:
            self._status.showMessage("")
            return

        self._event_info_panel.hide()
        self._detail_panel.show_defect(defect)

        item = self._circular_view._defect_items.get(defect.index)
        if item is not None:
            self._circular_view.select_defect_item(item)

        self._status.showMessage(
            f"Defect #{defect.defect_id}  |  "
            f"xenc={defect.x_encoder:.1f}  wenc={defect.w_encoder:.1f}  |  "
            f"r={defect.radius:.1f} μm  |  "
            f"SNR={defect.snr:.1f}"
        )

    def _on_defect_context_menu(self, defect: Defect):
        menu = QMenu(self)
        menu.setStyleSheet(LIGHT_THEME)

        view_events_action = menu.addAction("View Events")
        view_image_action = menu.addAction("View Image")

        pos = getattr(
            self._circular_view, "_last_right_click_global", None
        )
        action = menu.exec(pos if pos is not None else QCursor.pos())

        if action == view_events_action:
            self._show_event_regions(defect)
        elif action == view_image_action:
            self._show_defect_image_dialog(defect)

    def _show_event_regions(self, defect: Defect):
        if not self._data_folder:
            return

        if not self._event_array:
            try:
                self._status.showMessage("Loading events...")
                self._event_array = load_events(self._data_folder)
                self.set_status("events", True, len(self._event_array))
            except Exception as e:
                QMessageBox.critical(self, "Event Load Error", str(e))
                return

        self._circular_view.show_event_regions(defect, self._event_array)
        root_idx = defect.event_root_index
        chain = get_event_chain(root_idx, self._event_array)
        self._status.showMessage(
            f"Showing {len(chain)} event regions for defect #{defect.defect_id}"
        )

    def _on_view_all_events(self):
        """Show event regions for all defects."""
        if not self._data_folder:
            return

        if not self._event_array:
            try:
                self._status.showMessage("Loading events...")
                self._event_array = load_events(self._data_folder)
                self.set_status("events", True, len(self._event_array))
            except Exception as e:
                QMessageBox.critical(self, "Event Load Error", str(e))
                return

        for defect in self._defect_array:
            self._circular_view.show_event_regions(defect, self._event_array)
        self._status.showMessage(
            f"Showing event regions for {len(self._defect_array)} defects"
        )

    def _on_load_packet8M(self):
        """Load and display a packet8M .tt file — same canvas as View Image."""
        last_dir = getattr(self, "_last_packet8M_dir", os.getcwd())
        path, _ = QFileDialog.getOpenFileName(
            self, "Select packet8M File",
            last_dir, "Packet8M Files (*.tt);;All (*.*)",
        )
        if not path:
            return
        self._last_packet8M_dir = os.path.dirname(path)
        try:
            head, data, _enc, footer = load_packet8M(path)
        except Exception as e:
            QMessageBox.critical(self, "Load Error", str(e))
            return

        # normalize uint16 → uint8 for display
        d_f = data.astype(np.float64)
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

        # --- dialog ---
        MAX_SIZE = 800
        scale = MAX_SIZE / max(w, h)
        cw = int(w * scale)
        ch = int(h * scale)
        dialog = QDialog(self)
        dialog.setWindowTitle(
            f"Packet8M — {os.path.basename(path)}"
        )
        dialog.setAttribute(Qt.WA_DeleteOnClose)
        dialog.setMinimumSize(400, 300)
        dialog.adjustSize()

        main_layout = QVBoxLayout(dialog)

        # info bar
        info_right = QLabel("x=0, y=0, value=0")
        info_right.setStyleSheet(
            "padding:0px 4px; font-family:monospace; color:#555;"
        )

        # path label below canvas
        path_lbl = QLabel(f"Path: {path}")
        path_lbl.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        path_lbl.setStyleSheet(
            "padding:2px 2px; font-family:monospace; font-size:15px; color:#888;"
        )

        # QGraphicsView canvas
        scene = QGraphicsScene()
        gv = QGraphicsView(scene)
        gv.setFixedSize(cw + 2, ch + 2)
        gv.setFrameShape(QGraphicsView.Shape.NoFrame)
        gv.setStyleSheet(
            "background-color: #e8e8e8; border:1px solid #aaa;"
        )
        gv.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        gv.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        gv.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        gv.setTransformationAnchor(
            QGraphicsView.ViewportAnchor.AnchorUnderMouse
        )
        gv.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        gv.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        gv.viewport().setMouseTracking(True)

        pixmap_item = QGraphicsPixmapItem(pixmap)
        pixmap_item.setTransformationMode(
            Qt.TransformationMode.SmoothTransformation
        )
        scene.addItem(pixmap_item)
        scene.setSceneRect(QRectF(pixmap.rect()))

        # pixel tracking
        src_data = data.copy()
        display_bit_depth = 16

        def _pkt_filter(obj, event):
            if event.type() == QEvent.Type.MouseMove:
                sp = gv.mapToScene(event.pos())
                ix, iy = int(sp.x()), int(sp.y())
                if 0 <= ix < w and 0 <= iy < h:
                    val = int(src_data[iy, ix])
                    if display_bit_depth == 8:
                        val = val >> 8
                    info_right.setText(f"x={ix}, y={iy}, value={val}")
                else:
                    info_right.setText("x=0, y=0, value=0")
            elif event.type() == QEvent.Type.Leave:
                info_right.setText("x=0, y=0, value=0")
            elif event.type() == QEvent.Type.Wheel:
                delta = event.angleDelta().y()
                factor = 1.25 if delta > 0 else 0.8
                gv.scale(factor, factor)
                return True
            return False

        gv.viewport().installEventFilter(self)
        if not hasattr(self, "_dialog_filters"):
            self._dialog_filters = {}
            _orig = self.eventFilter

            def _global_filter(obj, event):
                cb = self._dialog_filters.get(obj)
                if cb:
                    return cb(obj, event)
                if _orig:
                    return _orig(obj, event)
                return False

            self.eventFilter = _global_filter

        self._dialog_filters[gv.viewport()] = _pkt_filter

        def _zoom_to_fit():
            gv.fitInView(scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

        home_btn = QPushButton("⌂")
        home_btn.setFixedSize(34, 24)
        home_btn.setStyleSheet(
            "QPushButton { background: rgba(250,250,248,235);"
            "border: 1px solid #c8c5c1; border-radius: 4px;"
            "font-size: 15px; font-weight: 700; color: #555;"
            "font-family: 'Segoe UI Symbol', 'Segoe UI', sans-serif;"
            "min-width: 30px; min-height: 24px; padding: 0px; }"
            "QPushButton:hover { background: rgba(224,222,219,240); }"
        )
        home_btn.setToolTip("Fit image to canvas")
        home_btn.clicked.connect(_zoom_to_fit)

        # right panel — head + footer info
        skip_keys = {"reserve2"}
        head_lines = ["<b>Head</b>"]
        for k, v in head.items():
            if k in skip_keys:
                continue
            head_lines.append(f"{k}: {v}")
        footer_lines = ["<b>Footer</b>"]
        for k, v in footer.items():
            if k in skip_keys:
                continue
            footer_lines.append(f"{k}: {v}")
        info_text = "<br>".join(head_lines + [""] + footer_lines)
        info_panel = QLabel(info_text)
        info_panel.setStyleSheet(
            "padding:4px 8px; font-family:monospace; font-size:15px;"
            "color:#555; background:transparent;"
        )
        info_panel.setFixedWidth(260)
        info_panel.setAlignment(Qt.AlignTop)

        # image processing panel
        proc_group = QFrame()
        proc_group.setStyleSheet(
            "QFrame { background:transparent; border:1px solid #ddd; border-radius:4px; }"
        )
        proc_layout = QVBoxLayout(proc_group)
        proc_layout.setContentsMargins(6, 4, 6, 4)
        proc_layout.setSpacing(2)

        proc_layout.addWidget(QLabel("<b>Processing</b>"))

        d_min = int(src_data.min())
        d_max = int(src_data.max())

        # histogram — red
        hist_w, hist_h = 245, 60
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
        hist_lbl.setFixedSize(hist_w, hist_h)
        proc_layout.addWidget(hist_lbl)

        hl = QHBoxLayout()
        hl.setContentsMargins(2, 0, 2, 0)
        lbl_hmin = QLabel(str(d_min))
        lbl_hmin.setStyleSheet("font-family:monospace; font-size:9px; color:#888;")
        lbl_hmax = QLabel(str(d_max))
        lbl_hmax.setAlignment(Qt.AlignRight)
        lbl_hmax.setStyleSheet("font-family:monospace; font-size:9px; color:#888;")
        hl.addWidget(lbl_hmin)
        hl.addWidget(lbl_hmax)
        proc_layout.addLayout(hl)

        def _slider_row(label, rmin, rmax, default):
            row = QHBoxLayout()
            lbl = QLabel(label + ":")
            lbl.setFixedWidth(40)
            row.addWidget(lbl)
            btn_m = QPushButton("−")
            btn_m.setFixedSize(20, 20)
            btn_m.setStyleSheet("padding:0px; font-size:12px;")
            row.addWidget(btn_m)
            sl = QSlider(Qt.Orientation.Horizontal)
            sl.setRange(rmin, rmax)
            sl.setValue(default)
            row.addWidget(sl)
            btn_p = QPushButton("+")
            btn_p.setFixedSize(20, 20)
            btn_p.setStyleSheet("padding:0px; font-size:12px;")
            row.addWidget(btn_p)
            val = QLabel(str(default))
            val.setFixedWidth(40)
            val.setStyleSheet("font-family:monospace; font-size:10px;")
            row.addWidget(val)
            btn_m.clicked.connect(lambda: sl.setValue(sl.value() - 1))
            btn_p.clicked.connect(lambda: sl.setValue(sl.value() + 1))
            return row, sl, val

        # min
        sl_range = max(1, d_max - d_min)
        min_row, min_sl, min_val = _slider_row("Min", 0, sl_range, 0)
        proc_layout.addLayout(min_row)

        # max
        max_row, max_sl, max_val = _slider_row("Max", 0, sl_range, sl_range)
        proc_layout.addLayout(max_row)

        # contrast
        ctr_row, ctr_sl, ctr_val = _slider_row("Ctr", 10, 300, 100)
        proc_layout.addLayout(ctr_row)

        # brightness
        brt_row, brt_sl, brt_val = _slider_row("Brt", -100, 100, 0)
        proc_layout.addLayout(brt_row)

        # Auto + Reset buttons
        btn_row = QHBoxLayout()
        btn_style = "QPushButton { padding:1px 0px; font-size:11px; min-height:20px; }"
        auto_btn = QPushButton("Auto")
        auto_btn.setStyleSheet(btn_style)
        reset_btn = QPushButton("Reset")
        reset_btn.setStyleSheet(btn_style)
        draw_btn = QPushButton("Draw")
        draw_btn.setStyleSheet(
            "QPushButton { padding:1px 0px; font-size:11px; min-height:20px;"
            "background: #b8d4f0; }"
        )

        def _on_draw():
            pkt_id = head["packet_id"]
            transposed = data.T.copy()
            d_f = transposed.astype(np.float64)
            lo, hi = _get_min_max()
            d_f = np.clip(d_f, lo, hi)
            if hi > lo:
                norm = ((d_f - lo) / (hi - lo) * 255).astype(np.uint8)
            else:
                norm = np.zeros_like(d_f, dtype=np.uint8)
            c = ctr_sl.value() / 100.0
            b = brt_sl.value()
            norm = np.clip(norm * c + b, 0, 255).astype(np.uint8)
            th, tw = norm.shape
            qimg = QImage(norm.tobytes(), tw, th, tw, QImage.Format.Format_Grayscale8)
            pixmap = QPixmap.fromImage(qimg)

            pkt_meta = find_packet_meta(pkt_id, self._packet_raw_meta_array)
            if pkt_meta is not None:
                x1, y1 = wenc_xenc_to_xy(pkt_meta.wenc_left, pkt_meta.xenc_outer)
                x2, y2 = wenc_xenc_to_xy(pkt_meta.wenc_right, pkt_meta.xenc_inner)
                self._circular_view.draw_packet8M_overlay(pixmap, x1, y1, x2, y2)
                self._circular_view.centerOn((x1 + x2) / 2, (y1 + y2) / 2)
            else:
                QMessageBox.warning(
                    dialog, "No Packet Meta",
                    "Please load packet_meta data first before drawing.",
                )

        draw_btn.clicked.connect(_on_draw)

        btn_row.addWidget(auto_btn)
        btn_row.addWidget(reset_btn)
        btn_row.addWidget(draw_btn)
        proc_layout.addLayout(btn_row)

        def _get_min_max():
            lo = d_min + min_sl.value()
            hi = d_min + max_sl.value()
            if hi <= lo:
                hi = lo + 1
            return lo, hi

        def _refresh_pixmap():
            lo, hi = _get_min_max()
            c = ctr_sl.value() / 100.0
            b = brt_sl.value()

            d_f = src_data.astype(np.float64)
            d_f = np.clip(d_f, lo, hi)
            if hi > lo:
                n = ((d_f - lo) / (hi - lo) * 255).astype(np.uint8)
            else:
                n = np.zeros_like(d_f, dtype=np.uint8)
            n = np.clip(n * c + b, 0, 255).astype(np.uint8)

            qimg = QImage(
                n.tobytes(), w, h, w, QImage.Format.Format_Grayscale8
            )
            pixmap_item.setPixmap(QPixmap.fromImage(qimg))
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
            # percentile-based range: includes both dark background & bright spots
            flat = src_data.ravel()
            new_lo = int(np.percentile(flat, 0.5))
            new_hi = int(np.percentile(flat, 99.5))
            if new_hi <= new_lo:
                new_lo, new_hi = d_min, d_max
            min_sl.setValue(max(0, new_lo - d_min))
            max_sl.setValue(min(sl_range, new_hi - d_min))
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

        _refresh_pixmap()  # initialize labels with data min/max

        # === layout: two columns ===
        main_layout.setContentsMargins(4, 0, 4, 0)
        main_layout.setSpacing(6)

        # --- left column ---
        left_col = QVBoxLayout()
        left_col.setContentsMargins(0, 0, 0, 0)
        left_col.setSpacing(0)

        # row1: home (left) + xy/value (right)
        toolbar_row = QHBoxLayout()
        toolbar_row.setContentsMargins(0, 0, 0, 0)
        toolbar_row.addWidget(home_btn)
        toolbar_row.addStretch()
        toolbar_row.addWidget(info_right)
        left_col.addLayout(toolbar_row)

        # row2: canvas
        left_col.addWidget(gv)
        left_col.addWidget(path_lbl)

        # --- right column ---
        right_col = QVBoxLayout()
        right_col.setContentsMargins(0, 18, 0, 0)
        right_col.setSpacing(4)

        # row1: head + footer info
        right_col.addWidget(info_panel)

        # row2: processing
        right_col.addWidget(proc_group)

        right_widget = QWidget()
        right_widget.setFixedWidth(260)
        right_widget.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed
        )
        right_widget.setLayout(right_col)

        # --- body ---
        left_widget = QWidget()
        left_widget.setFixedWidth(cw + 2)
        left_widget.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed
        )
        left_widget.setLayout(left_col)

        body = QHBoxLayout()
        body.setSpacing(8)
        body.addWidget(left_widget, 0, Qt.AlignmentFlag.AlignTop)
        body.addWidget(right_widget, 0, Qt.AlignmentFlag.AlignTop)
        body.addStretch()
        main_layout.addLayout(body)

        dialog.show()
        gv.fitInView(scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def _on_load_packet8M_toolbar(self):
        """Load and display a packet8M .tt file with transposed image."""
        last_dir = getattr(self, "_last_packet8M_dir", os.getcwd())
        path, _ = QFileDialog.getOpenFileName(
            self, "Select packet8M File",
            last_dir, "Packet8M Files (*.tt);;All (*.*)",
        )
        if not path:
            return
        self._last_packet8M_dir = os.path.dirname(path)
        try:
            head, data, _enc, footer = load_packet8M(path)
        except Exception as e:
            QMessageBox.critical(self, "Load Error", str(e))
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

        dialog = QDialog(self)
        dialog.setWindowTitle(
            f"Packet8M — {os.path.basename(path)}"
        )
        dialog.setAttribute(Qt.WA_DeleteOnClose)
        dialog.setMinimumSize(400, 300)

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

        def _zoom_to_fit():
            gv.fitInView(scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
            QTimer.singleShot(10, lambda: gv.fitInView(
                scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio))

        pkt_info = QLabel(
            f"packet_id: {head['packet_id']}, "
            f"valid_line={footer['valid_line']}, "
            f"valid_pixels={head['sensor_width']}"
        )
        pkt_info.setStyleSheet(
            "padding:0px 4px; font-family:monospace; font-size:12px; color:#555;"
        )

        top_row.addWidget(pkt_info)
        top_row.addStretch()
        top_row.addWidget(info_right)
        main_layout.addLayout(top_row)

        # --- canvas (native pixmap, fixed view height) ---
        FIXED_H = 600
        vh = FIXED_H
        vw = int(FIXED_H * w / h) if h > 0 else 500
        scene = QGraphicsScene()
        gv = QGraphicsView(scene)
        gv.setFixedSize(vw, vh)
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

        # right-click context menu
        _event_rect_items: list[QGraphicsItem] = []
        gv.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        def _on_context_menu(pos):
            menu = QMenu(gv)
            menu.addAction("Fit View", _zoom_to_fit)
            menu.addAction("View All Events", lambda: _view_all_events())
            menu.exec(gv.mapToGlobal(pos))
        gv.customContextMenuRequested.connect(_on_context_menu)

        def _view_all_events():
            for item in _event_rect_items:
                scene.removeItem(item)
            _event_rect_items.clear()
            pkt_id = head["packet_id"]
            if not self._data_folder:
                QMessageBox.warning(
                    dialog, "No Data", "Load data first.",
                )
                return
            if not self._event_array:
                try:
                    self._event_array = load_events(self._data_folder)
                    self.set_status("events", True, len(self._event_array))
                except Exception:
                    QMessageBox.warning(
                        dialog, "No Events",
                        "No events.csv found in the loaded data folder.",
                    )
                    return
            pen = QPen(QColor("#007bff"))
            pen.setCosmetic(True)
            pen.setWidthF(1.5)
            pen.setStyle(Qt.PenStyle.DashLine)
            for evt in self._event_array:
                if evt.packet_id == pkt_id:
                    # box coords: original pixels → transposed (1:1 native)
                    bx = evt.box_y
                    by = evt.box_x
                    bw = evt.box_height
                    bh = evt.box_width
                    rect_item = QGraphicsRectItem(bx, by, bw, bh)
                    rect_item.setPen(pen)
                    rect_item.setBrush(Qt.BrushStyle.NoBrush)
                    rect_item.setZValue(100)
                    scene.addItem(rect_item)
                    _event_rect_items.append(rect_item)

        main_layout.addWidget(gv)

        # --- path ---
        path_lbl = QLabel(f"Path: {path}")
        path_lbl.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        path_lbl.setStyleSheet(
            "padding:2px 2px; font-family:monospace; font-size:12px; color:#888;"
        )
        main_layout.addWidget(path_lbl)

        # --- bottom row: processing ---
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(8)

        # processing panel
        src_data = transposed.copy()

        proc_group = QFrame()
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
        lbl_hmax.setAlignment(Qt.AlignRight)
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
        draw_btn = QPushButton("Draw")
        draw_btn.setStyleSheet(
            "QPushButton { padding:1px 0px; font-size:11px; min-height:20px;"
            "background: #b8d4f0; }"
        )

        def _on_draw():
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

            pkt_meta = find_packet_meta(pkt_id, self._packet_raw_meta_array)
            if pkt_meta is not None:
                x1, y1 = wenc_xenc_to_xy(pkt_meta.wenc_left, pkt_meta.xenc_outer)
                x2, y2 = wenc_xenc_to_xy(pkt_meta.wenc_right, pkt_meta.xenc_inner)
                self._circular_view.draw_packet8M_overlay(pixmap2, x1, y1, x2, y2)
                self._circular_view.centerOn((x1 + x2) / 2, (y1 + y2) / 2)
            else:
                QMessageBox.warning(
                    dialog, "No Packet Meta",
                    "Please load packet_meta data first before drawing.",
                )

        draw_btn.clicked.connect(_on_draw)

        btn_row.addWidget(auto_btn)
        btn_row.addWidget(reset_btn)
        btn_row.addWidget(draw_btn)
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
            if event.type() == QEvent.Type.MouseMove:
                sp = gv.mapToScene(event.pos())
                ix, iy = int(sp.x()), int(sp.y())
                if 0 <= ix < w and 0 <= iy < h:
                    val = int(transposed[iy, ix])
                    if display_bit_depth == 8:
                        val = val >> 8
                    info_right.setText(f"x={ix}, y={iy}, value={val}")
                else:
                    info_right.setText("x=0, y=0, value=0")
            elif event.type() == QEvent.Type.Leave:
                info_right.setText("x=0, y=0, value=0")
            elif event.type() == QEvent.Type.Wheel:
                delta = event.angleDelta().y()
                factor = 1.25 if delta > 0 else 0.8
                gv.scale(factor, factor)
                return True
            return False

        gv.viewport().installEventFilter(self)
        if not hasattr(self, "_dialog_filters"):
            self._dialog_filters = {}
            _orig = self.eventFilter

            def _global_filter(obj, event):
                cb = self._dialog_filters.get(obj)
                if cb:
                    return cb(obj, event)
                if _orig:
                    return _orig(obj, event)
                return False

            self.eventFilter = _global_filter

        self._dialog_filters[gv.viewport()] = _pkt_filter

        bottom_row.addWidget(proc_group)
        bottom_row.addStretch()
        main_layout.addLayout(bottom_row)

        dialog.adjustSize()
        dialog.show()
        QTimer.singleShot(0, _zoom_to_fit)

    def _on_coord_compare(self):
        """Compute distance between calculated XY and stored (x,y)."""
        if not self._defect_array:
            QMessageBox.warning(self, "No Data", "Load data first.")
            return

        import math

        dists = []
        for d in self._defect_array:
            cx, cy = wenc_xenc_to_xy(d.w_encoder, d.x_encoder)
            dist = math.hypot(cx - d.x, cy - d.y)
            dists.append(dist)

        avg = sum(dists) / len(dists)
        self._show_distance_chart(dists, avg)

    def _show_distance_chart(self, dists, avg):
        """Show scatter plot with statistics in a QDialog."""
        import matplotlib
        matplotlib.use("Qt5Agg")
        from matplotlib import pyplot as plt
        from matplotlib.backends.backend_qt5agg import (
            FigureCanvasQTAgg as FigureCanvas,
        )
        from matplotlib.figure import Figure
        import numpy as np

        dists = np.array(dists)
        d_min = np.min(dists)
        d_max = np.max(dists)
        d_p2p = d_max - d_min

        fig = Figure(figsize=(7, 4.5))
        ax = fig.add_subplot(111)
        ax.set_title("Defect Distance Scatter", fontsize=11, fontweight="bold")
        ax.set_xlabel("Defect Index")
        ax.set_ylabel("Distance (d)")
        ax.scatter(
            range(len(dists)), dists, s=12, c="#2563a0",
            alpha=0.7, edgecolors="none",
        )
        ax.axhline(y=avg, color="#e67e22", linewidth=1.5,
                   linestyle="--", label=f"avg = {avg:.4f}")
        ax.legend(fontsize=9)
        fig.tight_layout()

        canvas = FigureCanvas(fig)

        # stats panel
        stats_widget = QWidget()
        stats_layout = QVBoxLayout(stats_widget)
        stats_layout.setContentsMargins(12, 12, 12, 12)
        stats_layout.setSpacing(6)

        title = QLabel("<b>Statistics</b>")
        stats_layout.addWidget(title)
        for label, value in [
            ("Total", str(len(dists))),
            ("Min", f"{d_min:.4f}"),
            ("Max", f"{d_max:.4f}"),
            ("P2P", f"{d_p2p:.4f}"),
            ("Average", f"{avg:.4f}"),
        ]:
            row = QHBoxLayout()
            row.addWidget(QLabel(label))
            val = QLabel(value)
            val.setStyleSheet("font-family: monospace;")
            row.addWidget(val)
            row.addStretch()
            stats_layout.addLayout(row)
        stats_layout.addStretch()

        # dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("Defect Distance Statistics")
        dialog.setMinimumSize(800, 400)
        dialog.setAttribute(Qt.WA_DeleteOnClose)

        def _on_close():
            plt.close(fig)

        dialog.finished.connect(_on_close)

        main_layout = QHBoxLayout(dialog)
        main_layout.addWidget(canvas, 3)
        main_layout.addWidget(stats_widget, 1)

        dialog.show()

    def _on_view_all_spiral(self):
        """Lazy-load packet data and draw spiral."""
        if not self._data_folder:
            return

        if not self._packet_raw_meta_array:
            try:
                self._status.showMessage("Loading packet metadata...")
                self._packet_raw_meta_array = load_packet_raw_meta(
                    self._data_folder
                )
                self.set_status(
                    "packet_meta", True, len(self._packet_raw_meta_array)
                )
            except Exception as e:
                QMessageBox.critical(
                    self, "Packet Load Error", str(e)
                )
                return

        # set packets on circular view
        self._circular_view._packet_raw_meta_array = (
            self._packet_raw_meta_array
        )

        from PySide6.QtWidgets import QProgressDialog, QApplication

        total = len(self._packet_raw_meta_array)
        progress = QProgressDialog(
            "Rendering spiral...", "Cancel", 0, total, self
        )
        progress.setWindowTitle("Please wait")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        progress.setValue(0)

        def update_progress(current, maximum):
            progress.setMaximum(maximum)
            progress.setValue(current)
            QApplication.processEvents()

        bad_count = self._circular_view.draw_spiral_from_packets(
            update_progress
        )
        progress.close()

        if bad_count > 0:
            QMessageBox.warning(
                self,
                "Spiral Warning",
                f"{bad_count} spiral segment(s) skipped — "
                f"wenc span or xenc span >= 2000.",
            )

    def _ensure_img_meta_loaded(self):
        if self._img_meta_array or not self._data_folder:
            return
        try:
            self._img_meta_array = load_image_meta(self._data_folder)
            self.set_status("img_meta", True, len(self._img_meta_array))
            self._status.showMessage(
                f"Loaded {len(self._img_meta_array)} image metas (lazy)"
            )
        except FileNotFoundError:
            pass  # csv not present — leave array empty
        except Exception as e:
            QMessageBox.critical(self, "Image Meta Load Error", str(e))

    def _show_defect_image_dialog(self, defect: Defect):
        if not self._data_folder:
            return

        self._ensure_img_meta_loaded()

        idx = defect.img_id - 1
        if idx < 0 or idx >= len(self._img_meta_array):
            QMessageBox.warning(
                self,
                "Not Found",
                f"ImageMeta index {idx} (img_id={defect.img_id}) "
                f"out of range (loaded {len(self._img_meta_array)} metas).",
            )
            return

        img_meta = self._img_meta_array[idx]

        # --- build dialog ---
        dialog = QDialog(self)
        dialog.setWindowTitle(
            f"Defect #{defect.defect_id}  —  Image #{img_meta.img_id}"
        )
        dialog.setMinimumSize(780, 600)
        dialog.setAttribute(Qt.WA_DeleteOnClose)

        main_layout = QVBoxLayout(dialog)

        # ===== ImageMeta table (1 data row, value-only) =====
        im_cols = [
            "index", "img_id", "is_valid", "scale", "proc_id", "file_name",
            "pos", "angle_deg", "overlap_prev", "overlap_next",
            "tag", "packet_count",
        ]
        im_values = [
            str(idx), str(img_meta.img_id), str(img_meta.is_valid),
            f"{img_meta.scale:.3f}", str(img_meta.proc_id),
            img_meta.file_name, str(img_meta.pos),
            f"{img_meta.angle_deg:.3f}", str(img_meta.overlap_pixels_prev),
            str(img_meta.overlap_pixels_next), str(img_meta.tag),
            str(img_meta.packet_array_count),
        ]

        im_table = QTableWidget(1, len(im_cols))
        im_table.setHorizontalHeaderLabels(im_cols)
        im_table.verticalHeader().setVisible(False)
        for j, val in enumerate(im_values):
            item = QTableWidgetItem(val)
            item.setFlags(Qt.ItemIsEnabled)
            im_table.setItem(0, j, item)
        im_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        im_table.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)
        im_table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        im_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        main_layout.addWidget(im_table)

        # small gap between tables
        main_layout.addSpacing(4)

        # ===== PacketMeta table =====
        pk_cols = [
            "pkg_idx", "pkt_id", "proc_id", "center",
            "pkg_row_start", "pkg_row_end",
            "pkg_col_start", "pkg_col_end",
            "img_row_start", "img_col_start",
            "img_row_count", "img_col_count",
        ]
        n_pkts = len(img_meta.packet_array)
        pk_table = QTableWidget(n_pkts, len(pk_cols))
        pk_table.setHorizontalHeaderLabels(pk_cols)

        vh_labels = [
            f"Pkt[{img_meta.packet_array[k].pkg_index}]"
            for k in range(n_pkts)
        ]
        pk_table.setVerticalHeaderLabels(vh_labels)

        for k, p in enumerate(img_meta.packet_array):
            vals = [
                str(p.pkg_index), str(p.packet_id),
                str(p.from_proc_id), str(p.is_center),
                str(p.pkg_row_start), str(p.pkg_row_end),
                str(p.pkg_col_start), str(p.pkg_col_end),
                str(p.img_row_start), str(p.img_col_start),
                str(p.img_row_count), str(p.img_col_count),
            ]
            for j, val in enumerate(vals):
                item = QTableWidgetItem(val)
                item.setFlags(Qt.ItemIsEnabled)
                pk_table.setItem(k, j, item)

        pk_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeToContents
        )
        pk_table.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)
        pk_table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        pk_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        main_layout.addWidget(pk_table)

        # ===== image section =====
        IMG_SIZE = 400

        # info labels created early — added to layout later
        info_left = QLabel("0×0 pixels, 0-bit; 0K")
        info_left.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        info_left.setStyleSheet(
            "padding:1px 0px 1px 2px; background:transparent; font-family:monospace;"
        )
        info_right = QLabel("x=0, y=0, value=0")
        info_right.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        info_right.setStyleSheet(
            "padding:1px 2px 1px 0px; background:transparent; color:#333; font-family:monospace;"
        )

        # path label below canvas — created early, added to layout later
        path_label = QLabel("")
        path_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        path_label.setStyleSheet(
            "padding:0px; background:transparent; font-family:monospace; "
            "color:#555;"
        )
        path_label.setFixedWidth(IMG_SIZE + 4)
        path_label.setWordWrap(True)

        # QGraphicsView for image — same approach as main defect canvas
        scene = QGraphicsScene()
        gv = QGraphicsView(scene)
        gv.setFixedSize(IMG_SIZE + 4, IMG_SIZE + 4)
        gv.setStyleSheet(
            "background-color: #e8e8e8; border:1px solid #aaa; border-top:none;"
        )
        gv.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        gv.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        gv.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        gv.setTransformationAnchor(
            QGraphicsView.ViewportAnchor.AnchorUnderMouse
        )
        gv.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        gv.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        gv.setViewportUpdateMode(
            QGraphicsView.ViewportUpdateMode.FullViewportUpdate
        )

        pixmap_item = QGraphicsPixmapItem()
        pixmap_item.setTransformationMode(
            Qt.TransformationMode.SmoothTransformation
        )
        scene.addItem(pixmap_item)

        # pixel tracking state
        source_image: QImage | None = None
        source_data: np.ndarray | None = None
        _display_norm_buffer: np.ndarray | None = None  # keep alive for QImage
        view_image_path: str = ""
        view_file_size: int = 0
        display_bit_depth: int = 16

        def _load_source_image(path: str):
            nonlocal source_image, source_data
            reader = QImage(path)
            if reader.isNull():
                return False
            fmt = reader.format()
            if fmt in (QImage.Format.Format_Grayscale16, QImage.Format.Format_Grayscale8):
                source_image = reader.copy()
            else:
                source_image = reader.convertToFormat(QImage.Format.Format_Grayscale16)
            w, h = source_image.width(), source_image.height()
            if source_image.depth() == 16:
                ptr = source_image.constBits()
                arr = np.frombuffer(ptr, dtype=np.uint16, count=w * h)
                source_data = arr.reshape((h, w)).copy()
            else:
                ptr = source_image.constBits()
                arr = np.frombuffer(ptr, dtype=np.uint8, count=w * h)
                source_data = arr.reshape((h, w)).astype(np.uint16).copy()
            return True

        def _build_display_qimage():
            nonlocal _display_norm_buffer
            if source_data is None:
                return QImage()
            data_f = source_data.astype(np.float64)
            d_min, d_max = data_f.min(), data_f.max()
            if d_max > d_min:
                _display_norm_buffer = (
                    (data_f - d_min) / (d_max - d_min) * 255
                ).astype(np.uint8)
            else:
                _display_norm_buffer = np.zeros_like(data_f, dtype=np.uint8)
            h, w = _display_norm_buffer.shape
            return QImage(
                _display_norm_buffer.data, w, h, w,
                QImage.Format.Format_Grayscale8,
            )

        def _refresh_image():
            if not view_image_path or not os.path.isfile(view_image_path):
                pixmap_item.setPixmap(QPixmap())
                info_left.setText("0×0 pixels, 0-bit; 0K")
                info_right.setText("x=0, y=0, value=0")
                path_label.setText("")
                return
            if not _load_source_image(view_image_path):
                pixmap_item.setPixmap(QPixmap())
                path_label.setText(view_image_path)
                return

            disp_img = _build_display_qimage()
            pixmap = QPixmap.fromImage(disp_img)
            pixmap_item.setPixmap(pixmap)
            scene.setSceneRect(QRectF(pixmap.rect()))

            w, h = source_image.width(), source_image.height()
            depth_label = "16-bit" if display_bit_depth == 16 else "8-bit"
            kb = view_file_size // 1024 if view_file_size else 0
            info_left.setText(f"{w}×{h} pixels; {depth_label}; {kb}K")
            path_label.setText(view_image_path)

        def _bit_depth_changed(idx: int):
            nonlocal display_bit_depth
            display_bit_depth = 8 if idx == 1 else 16
            _refresh_image()

        def _zoom_to_fit():
            if not view_image_path:
                return
            if source_image is None:
                _refresh_image()
            if source_image is None:
                return
            gv.fitInView(scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

        # event filter for pixel tracking only (zoom + pan handled natively)
        gv.viewport().setMouseTracking(True)
        info_right_default = "x=0, y=0, value=0"

        def _image_event_filter(obj, event):
            t = event.type()
            if t == QEvent.Type.MouseMove:
                if source_data is not None and source_image is not None:
                    sp = gv.mapToScene(event.pos())
                    ix = int(sp.x())
                    iy = int(sp.y())
                    if (
                        0 <= ix < source_image.width()
                        and 0 <= iy < source_image.height()
                    ):
                        val = int(source_data[iy, ix])
                        if display_bit_depth == 8:
                            val = val >> 8
                        info_right.setText(
                            f"x={ix}, y={iy}, value={val}"
                        )
                    else:
                        info_right.setText(info_right_default)
                else:
                    info_right.setText(info_right_default)
            elif t == QEvent.Type.Leave:
                info_right.setText(info_right_default)
            elif t == QEvent.Type.Wheel:
                delta = event.angleDelta().y()
                factor = 1.25 if delta > 0 else 0.8
                gv.scale(factor, factor)
                return True
            return False

        gv.viewport().installEventFilter(self)
        dialog._img_event_filter = _image_event_filter

        if not hasattr(self, "_dialog_filters"):
            self._dialog_filters = {}
            _orig = self.eventFilter

            def _global_filter(obj, event):
                cb = self._dialog_filters.get(obj)
                if cb is not None:
                    return cb(obj, event)
                if _orig:
                    return _orig(obj, event)
                return False

            self.eventFilter = _global_filter

        self._dialog_filters[gv.viewport()] = _image_event_filter

        def _browse():
            nonlocal view_image_path, view_file_size
            path, _ = QFileDialog.getOpenFileName(
                dialog,
                "Select Image File",
                img_folder if os.path.isdir(img_folder) else os.getcwd(),
                "Images (*.png *.jpg *.jpeg *.bmp *.tiff *.tif);;All (*.*)",
            )
            if path:
                view_image_path = path
                view_file_size = os.path.getsize(path)
                QApplication.processEvents()
                _zoom_to_fit()

        # load initial image
        img_folder = os.path.join(self._data_folder, "defect_img")
        auto_path = os.path.join(img_folder, img_meta.file_name)
        if os.path.isfile(auto_path):
            view_image_path = auto_path
            view_file_size = os.path.getsize(auto_path)
        else:
            view_image_path = ""
            view_file_size = 0

        # --- spacing before controls ---
        main_layout.addSpacing(4)

        # --- image controls row ---
        ctrl_layout = QHBoxLayout()

        ctrl_layout.addWidget(QLabel("Bit Depth:"))
        bit_combo = QComboBox()
        bit_combo.addItems(["16-bit", "8-bit"])
        bit_combo.setCurrentIndex(0 if display_bit_depth == 16 else 1)
        bit_combo.currentIndexChanged.connect(_bit_depth_changed)
        ctrl_layout.addWidget(bit_combo)

        ctrl_layout.addSpacing(12)

        load_btn = QPushButton("Load Image")
        load_btn.setStyleSheet(
            "QPushButton { padding:2px 6px; }"
        )
        load_btn.setSizePolicy(
            QSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        )
        load_btn.clicked.connect(_browse)
        ctrl_layout.addWidget(load_btn)

        ctrl_layout.addSpacing(4)

        home_btn = QPushButton("⌂")
        home_btn.setFixedSize(34, 24)
        home_btn.setStyleSheet(
            "QPushButton { background: rgba(250,250,248,235);"
            "border: 1px solid #c8c5c1; border-radius: 4px;"
            "font-size: 15px; font-weight: 700; color: #555;"
            "font-family: 'Segoe UI Symbol', 'Segoe UI', sans-serif;"
            "min-width: 30px; min-height: 24px; padding: 0px; }"
            "QPushButton:hover { background: rgba(224,222,219,240); }"
        )
        home_btn.setToolTip("Fit image to canvas")
        home_btn.clicked.connect(_zoom_to_fit)
        ctrl_layout.addWidget(home_btn)

        ctrl_layout.addStretch()
        main_layout.addLayout(ctrl_layout)

        # --- info bar (seamless with canvas) ---
        info_bar = QHBoxLayout()
        info_bar.setContentsMargins(0, 0, 0, 0)
        info_bar.setSpacing(0)
        info_bar.addWidget(info_left)
        info_bar.addWidget(info_right)

        info_frame = QFrame()
        info_frame.setLayout(info_bar)
        info_frame.setFixedWidth(IMG_SIZE + 4)
        info_frame.setStyleSheet(
            "QFrame { background:transparent; border:none; }"
        )
        main_layout.addWidget(info_frame)

        # image display area
        main_layout.addWidget(gv)
        main_layout.addWidget(path_label)
        main_layout.setSpacing(0)

        # prevent window resizing
        dialog.layout().setSizeConstraint(
            QLayout.SizeConstraint.SetFixedSize
        )

        dialog.show()

        # flush pending events so dialog is fully visible
        QApplication.processEvents()
        _zoom_to_fit()

    def _load_packet_for_defect(self, defect: Defect):
        if not self._data_folder:
            return

        pkt_meta = find_packet_meta(
            defect.peak_packet_id, self._packet_raw_meta_array
        )
        if pkt_meta is None:
            QMessageBox.warning(
                self,
                "Not Found",
                f"Packet #{defect.peak_packet_id} not found in metadata.",
            )
            return

        img_folder = os.path.join(self._data_folder, "img")
        if not os.path.isdir(img_folder):
            img_folder = self._data_folder

        img_path = os.path.join(
            img_folder, f"packet_{defect.peak_packet_id}.bin"
        )

        if not os.path.exists(img_path):
            QMessageBox.warning(
                self,
                "Not Found",
                f"Image file not found:\n{img_path}",
            )
            return

        try:
            head, data, _enc, footer = load_packet8M(img_path)
            packet_image = PacketImage(
                packet_id=defect.peak_packet_id,
                head=head,
                data=data,
                footer=footer,
            )
            self._circular_view.load_packet_image(defect, packet_image)
            self._status.showMessage(
                f"Loaded packet image #{defect.peak_packet_id}  |  "
                f"{data.shape[1]}x{data.shape[0]} pixels"
            )
        except Exception as e:
            QMessageBox.critical(self, "Image Load Error", str(e))
