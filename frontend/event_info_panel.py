"""Panel showing event details, positioned in the right column."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QFrame,
    QPushButton,
)
from PySide6.QtCore import Qt, Signal

from backend.models import Event


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
            f"defect_id: {event.defect_id}",
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
