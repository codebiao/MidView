"""Main application window for PacketView."""

from __future__ import annotations

import os
from PySide6.QtWidgets import (
    QMainWindow,
    QToolBar,
    QStatusBar,
    QSplitter,
    QFileDialog,
    QMessageBox,
    QMenu,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QFrame,
    QPushButton,
)
from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtGui import QAction, QCursor

from frontend.circular_view import CircularView, wenc_xenc_to_xy
from frontend.detail_panel import DetailPanel
from frontend.theme import LIGHT_THEME
from backend.models import Defect, Event, PacketRawMeta, PacketImage
from backend.data_load.defect_loader import load_defects
from backend.data_load.event_loader import load_events, get_event_chain
from backend.data_load.packet_loader import (
    load_packet_raw_meta,
    find_packet_meta,
)
from backend.unpacking8M import parser_8M


class EventInfoPanel(QWidget):
    """Panel showing event details, positioned in the right column."""

    closed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(300)
        self.setMaximumWidth(420)
        self.setStyleSheet(
            "EventInfoPanel { background-color: #e8e8e5; }"
        )
        self.hide()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # header
        header = QWidget()
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(8, 4, 4, 4)

        title = QLabel("Event Info")
        title.setObjectName("sectionTitle")
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

        # scrollable content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
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
        self.setWindowTitle("PacketView — Wafer Defect Visualization")
        self.resize(1400, 900)
        self.setMinimumSize(1000, 600)
        self.setStyleSheet(LIGHT_THEME)

        self._data_folder: str | None = None
        self._defect_array: list[Defect] = []
        self._event_array: list[Event] = []
        self._packet_raw_meta_array: list[PacketRawMeta] = []

        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(2)

        self._circular_view = CircularView()

        # right column: detail panel + event info panel
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        self._detail_panel = DetailPanel()
        self._event_info_panel = EventInfoPanel()

        right_layout.addWidget(self._detail_panel)
        right_layout.addWidget(self._event_info_panel)

        splitter.addWidget(self._circular_view)
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
            self._packet_raw_meta_array = load_packet_raw_meta(folder)
            self._event_array = []

            self._data_folder = folder
            self._circular_view.load_data(
                self._defect_array,
                self._packet_raw_meta_array,
            )

            n_defects = len(self._defect_array)
            n_packets = len(self._packet_raw_meta_array)
            self._status.showMessage(
                f"Loaded {n_defects} defects, {n_packets} packets "
                f"from {folder}"
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

        pos = getattr(
            self._circular_view, "_last_right_click_global", None
        )
        action = menu.exec(pos if pos is not None else QCursor.pos())

        if action == view_events_action:
            self._show_event_regions(defect)

    def _show_event_regions(self, defect: Defect):
        if not self._data_folder:
            return

        if not self._event_array:
            try:
                self._status.showMessage("Loading events...")
                self._event_array = load_events(self._data_folder)
            except Exception as e:
                QMessageBox.critical(self, "Event Load Error", str(e))
                return

        self._circular_view.show_event_regions(defect, self._event_array)
        root_idx = defect.event_root_index
        chain = get_event_chain(root_idx, self._event_array)
        self._status.showMessage(
            f"Showing {len(chain)} event regions for defect #{defect.defect_id}"
        )

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
            head, data, footer = parser_8M(img_path)
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
