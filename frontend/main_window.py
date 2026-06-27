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
    QFrame,
    QPushButton,
    QTextEdit,
    QApplication,
    QSizePolicy,
)
from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtGui import QAction, QCursor

from frontend import global_param as _cfg
from frontend.circular_view import CircularView
from frontend.xwenc_to_xy import xwenc_to_xy
from frontend.detail_panel import DetailPanel
from frontend.event_info_panel import EventInfoPanel
from frontend.theme import LIGHT_THEME
from frontend.packet8m_viewer import show_packet8m_viewer
from frontend.defect_image_viewer import show_defect_image_dialog
from frontend.compare_csv_dialog import show_compare_csv_dialog
from frontend.distance_chart_dialog import compute_distances, show_distance_chart
from frontend.my_param_dialog import show_my_param_dialog
from backend.models import Defect, Event, PacketRawMeta, ImageMeta
from backend.data_load.defect_loader import load_defects
from backend.data_load.event_loader import load_events, get_event_chain
from backend.data_load.packet_raw_meta_loader import (
    load_packet_raw_meta,
)
from backend.data_load.image_meta_loader import load_image_meta
from backend.data_load.my_param_loader import load_my_param


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MidView — Wafer Defect Visualization")
        screen_geo = self.screen().availableGeometry()
        height = screen_geo.height() * 8 // 9
        win_w = height + 400
        win_h = height
        win_x = screen_geo.x() + (screen_geo.width() - win_w) // 2
        win_y = screen_geo.y() + (screen_geo.height() - win_h) // 2
        self.setGeometry(win_x, win_y, win_w, win_h)
        self.setMinimumSize(1000, 600)
        self.setStyleSheet(LIGHT_THEME)

        self._data_folder: str | None = None
        self._defect_array: list[Defect] = []
        self._event_array: list[Event] = []
        self._packet_raw_meta_array: list[PacketRawMeta] = []
        self._img_meta_array: list[ImageMeta] = []
        self._my_param: dict | None = None

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

        # my_param button (clickable, placed first)
        self._my_param_btn = QPushButton("MyParam: 0")
        self._my_param_btn.setFlat(True)
        self._my_param_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._my_param_btn.setStyleSheet(
            "QPushButton { background: #d8d6d2; color: #888; padding: 2px 10px;"
            "border-radius: 3px; font-size: 11px; font-family: monospace;"
            "border: none; }"
            "QPushButton:hover { color: #2563a0; text-decoration: underline; }"
        )
        self._my_param_btn.clicked.connect(self._on_my_param_clicked)
        status_layout.addWidget(self._my_param_btn)

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
        analysis_menu.addAction(coord_compare_action)
        compare_csv_action = QAction("Compare Csv", self)
        compare_csv_action.triggered.connect(self._on_compare_csv)
        analysis_menu.addAction(compare_csv_action)

        analysis_btn = QPushButton("Analysis")
        analysis_btn.setMenu(analysis_menu)
        analysis_btn.setStyleSheet(
            "QPushButton { padding: 3px 12px; font-size: 12px; }"
        )
        toolbar.addWidget(analysis_btn)

        # Tools menu
        tools_menu = QMenu("Tools", self)
        measure_action = QAction("Measure Distance", self)
        measure_action.triggered.connect(self._on_measure_distance)
        tools_menu.addAction(measure_action)

        from PySide6.QtWidgets import QToolButton
        tools_btn = QToolButton()
        tools_btn.setText("Tools")
        tools_btn.setMenu(tools_menu)
        tools_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        tools_btn.setStyleSheet(
            "QToolButton { padding: 3px 12px; font-size: 12px; }"
        )
        toolbar.addWidget(tools_btn)

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
        self._circular_view.event_region_clicked.connect(
            self._on_event_region_show_coords
        )
        self._circular_view.view_all_events_requested.connect(
            self._on_view_all_events
        )
        self._circular_view.view_all_spiral_requested.connect(
            self._on_view_all_spiral
        )

    def set_status(self, key: str, loaded: bool, count: int = 0):
        """Update a data-status label."""
        if key == "my_param":
            btn = self._my_param_btn
            if loaded:
                btn.setText("MyParam")
                btn.setStyleSheet(
                    "QPushButton { background: #cce5cc; color: #2a6e2a; padding: 2px 10px;"
                    "border-radius: 3px; font-size: 11px; font-family: monospace;"
                    "border: none; }"
                    "QPushButton:hover { color: #2563a0; text-decoration: underline; }"
                )
            else:
                btn.setText("MyParam: 0")
                btn.setStyleSheet(
                    "QPushButton { background: #d8d6d2; color: #888; padding: 2px 10px;"
                    "border-radius: 3px; font-size: 11px; font-family: monospace;"
                    "border: none; }"
                    "QPushButton:hover { color: #2563a0; text-decoration: underline; }"
                )
            return
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

    def _on_my_param_clicked(self):
        """Show MyParam struct contents in a dialog."""
        show_my_param_dialog(self, self._my_param)

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

        sx, sy = xwenc_to_xy(match.x_encoder, match.w_encoder)
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
            self._packet_raw_meta_array = []
            self._img_meta_array = []
            self._event_array = []
            self._my_param = None
            self._data_folder = folder

            # load my_param first — must set xenc_start/scan_start_radius before loading defects
            self._my_param = load_my_param(os.path.join(folder, "my_param.json"))
            if self._my_param is not None:
                _cfg.my_param = self._my_param
            self.set_status("my_param", self._my_param is not None)

            self._defect_array = load_defects(folder)
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
        view_rect_action = menu.addAction("View Rect Area")
        menu.addSeparator()
        clear_events_action = menu.addAction("Clear Events")
        clear_rect_action = menu.addAction("Clear Rect Area")

        pos = getattr(
            self._circular_view, "_last_right_click_global", None
        )
        action = menu.exec(pos if pos is not None else QCursor.pos())

        if action == view_events_action:
            self._show_event_regions(defect)
        elif action == view_image_action:
            self._show_defect_image_dialog(defect)
        elif action == view_rect_action:
            self._circular_view.show_defect_rect_area(defect)
        elif action == clear_rect_action:
            self._circular_view.clear_defect_rect_area()
        elif action == clear_events_action:
            self._circular_view.clear_defect_events(defect.index)

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

    def _on_event_region_show_coords(self, event):
        if event is None:
            return
        cx, cy = xwenc_to_xy(event.x_encoder, event.w_encoder)
        self._status.showMessage(
            f"Event (x={cx:.1f}, y={cy:.1f})  |  "
            f"xenc={event.x_encoder:.1f}, wenc={event.w_encoder:.1f}"
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

    def _on_load_packet8M_toolbar(self):
        """Load and display a packet8M .tt file with transposed image."""
        show_packet8m_viewer(self)

    def _on_coord_compare(self):
        """Compute distance between calculated XY and stored (x,y)."""
        if not self._defect_array:
            QMessageBox.warning(self, "No Data", "Load data first.")
            return

        dists = compute_distances(self._defect_array)
        avg = sum(dists) / len(dists)
        show_distance_chart(self, dists, avg)

    def _on_measure_distance(self):
        """Measure distance between two points on the canvas."""
        self._status.showMessage("Measure mode: click two points on canvas")
        self._circular_view.start_measure_distance()

    def _on_compare_csv(self):
        """Open a window to compare CSV files side by side."""
        show_compare_csv_dialog(self)

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
        show_defect_image_dialog(self, defect)
