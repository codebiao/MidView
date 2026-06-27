"""Panel showing event details, positioned in the right column."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QScrollArea,
    QFrame,
    QPushButton,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor

from backend.models import Event
from frontend.xwenc_to_xy import xwenc_to_xy


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
        self._scroll = scroll
        self._scroll_widget: QWidget | None = None
        layout.addWidget(scroll)

    def _clear_scroll_content(self):
        if self._scroll_widget is not None:
            self._scroll_widget.deleteLater()
            self._scroll_widget = None

    def show_event(self, event: Event):
        if event is None:
            self.hide()
            return
        self._clear_scroll_content()
        enc_x, enc_y = xwenc_to_xy(event.x_encoder, event.w_encoder)

        content = QWidget()
        grid = QGridLayout(content)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 2)
        grid.setSpacing(0)
        grid.setContentsMargins(4, 0, 4, 0)

        attrs = [
            ("index", str(event.index)),
            ("this_ptr", str(event.this_ptr)),
            ("parent", str(event.parent)),
            ("next", str(event.next)),
            ("prev", str(event.prev)),
            ("next_track", str(event.next_track)),
            ("prev_track", str(event.prev_track)),
            ("track_root", str(event.track_root)),
            ("count", str(event.count)),
            ("track_count", str(event.track_count)),
            ("track_node_count", str(event.track_node_count)),
            ("status", str(event.status)),
            ("track_id", str(event.track_id)),
            ("event_id", str(event.event_id)),
            ("defect_id", str(event.defect_id)),
            ("proc_id", str(event.proc_id)),
            ("packet_id", str(event.packet_id)),
            ("peak_adc", f"{event.peak_adc:.1f}"),
            ("peak_row", f"{event.peak_row:.1f}"),
            ("peak_col", f"{event.peak_col:.1f}"),
            ("x_encoder", f"{event.x_encoder:.1f}"),
            ("w_encoder", f"{event.w_encoder:.1f}"),
            ("radius", f"{event.radius:.1f}"),
            ("theta", f"{event.theta:.4f}"),
            ("x_cor", f"{event.x_cor:.1f}"),
            ("y_cor", f"{event.y_cor:.1f}"),
            ("x", f"{event.x:.1f}"),
            ("y", f"{event.y:.1f}"),
            ("enc_to_x", f"{enc_x:.1f}"),
            ("enc_to_y", f"{enc_y:.1f}"),
            ("snr", f"{event.snr:.1f}"),
            ("ee", f"{event.ee:.6f}"),
            ("ee_is_fitted", str(event.ee_is_fitted)),
            ("xenc_merge_count", f"{event.xenc_merge_count:.1f}"),
            ("wenc_merge_count", f"{event.wenc_merge_count:.1f}"),
            ("wenc_per_um", f"{event.wenc_per_um:.3f}"),
            ("box_x", f"{event.box_x:.1f}"),
            ("box_y", f"{event.box_y:.1f}"),
            ("box_width", f"{event.box_width:.1f}"),
            ("box_height", f"{event.box_height:.1f}"),
            ("compressed2_box_x", f"{event.compressed2_box_x:.1f}"),
            ("compressed2_box_y", f"{event.compressed2_box_y:.1f}"),
            ("compressed2_box_width", f"{event.compressed2_box_width:.1f}"),
            ("compressed2_box_height", f"{event.compressed2_box_height:.1f}"),
            ("xenc_outer", f"{event.xenc_outer:.1f}"),
            ("xenc_inner", f"{event.xenc_inner:.1f}"),
            ("wenc_left", f"{event.wenc_left:.1f}"),
            ("wenc_right", f"{event.wenc_right:.1f}"),
            ("acc_flag", str(event.acc_flag)),
            ("cosmic_ray_flag", str(event.cosmic_ray_flag)),
            ("saturated_flag", str(event.saturated_flag)),
            ("pixel_sindex", str(event.pixel_sindex)),
            ("pixel_eindex", str(event.pixel_eindex)),
        ]

        for row, (name, value) in enumerate(attrs):
            lbl = QLabel(name)
            lbl.setObjectName("fieldLabel")
            val = QLabel(value)
            val.setObjectName("fieldValue")
            val.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextSelectableByMouse
            )
            if name in ("enc_to_x", "enc_to_y"):
                lbl.setStyleSheet("color: #dc3545;")
                val.setStyleSheet("color: #dc3545;")
            grid.addWidget(lbl, row, 0)
            grid.addWidget(val, row, 1)

        grid.setRowStretch(len(attrs), 1)
        self._scroll.setWidget(content)
        self._scroll_widget = content
        self.show()

    def _on_close(self):
        self.hide()
        self.closed.emit()
