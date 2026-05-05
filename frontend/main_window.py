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
)
from PySide6.QtCore import Qt, QSize
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
        self._detail_panel = DetailPanel()

        splitter.addWidget(self._circular_view)
        splitter.addWidget(self._detail_panel)
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

        # center on defect
        sx, sy = wenc_xenc_to_xy(match.w_encoder, match.x_encoder)
        self._circular_view.centerOn(sx, sy)

        # select defect
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
