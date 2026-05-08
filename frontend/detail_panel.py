"""Right-side detail panel with search and defect information."""

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QFrame,
    QGridLayout,
    QComboBox,
    QLineEdit,
    QPushButton,
)
from PySide6.QtCore import Qt, Signal
from backend.models import Defect, Event

SEARCH_FIELDS = [
    "defect_id",
    "event_root_index",
    "from_channel",
    "channel_defect_id",
    "related_defect_id",
    "img_id",
    "img_tag",
    "peak_packet_id",
    "cluster_number",
    "midlevel_bin_number",
    "rough_bin_number",
    "fine_bin_number",
]


class DetailPanel(QWidget):
    """Panel with search bar and scrollable defect properties."""

    search_requested = Signal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(300)
        self.setMaximumWidth(420)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)

        # --- search bar ---
        search_widget = QWidget()
        search_layout = QHBoxLayout(search_widget)
        search_layout.setContentsMargins(4, 2, 4, 2)
        search_layout.setSpacing(4)

        self._field_combo = QComboBox()
        self._field_combo.addItems(SEARCH_FIELDS)
        self._field_combo.setMinimumWidth(130)
        self._field_combo.setStyleSheet(
            "QComboBox { font-size: 11px; padding: 2px 4px; }"
        )

        self._value_edit = QLineEdit()
        self._value_edit.setPlaceholderText("Value...")
        self._value_edit.setStyleSheet(
            "QLineEdit { font-size: 11px; padding: 2px 6px; }"
        )

        self._search_btn = QPushButton("Search")
        self._search_btn.setStyleSheet(
            "QPushButton { font-size: 11px; padding: 2px 8px; }"
        )
        self._search_btn.clicked.connect(self._on_search)
        self._value_edit.returnPressed.connect(self._on_search)

        search_layout.addWidget(self._field_combo)
        search_layout.addWidget(self._value_edit)
        search_layout.addWidget(self._search_btn)

        self._layout.addWidget(search_widget)

        # --- title bar ---
        title_bar = QWidget()
        title_bar.setStyleSheet("background-color: #d8d6d2;")
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(8, 4, 8, 4)

        self._title_label = QLabel("Defect Info")
        self._title_label.setObjectName("sectionTitle")
        self._title_label.setStyleSheet("background: transparent;")
        title_layout.addWidget(self._title_label)
        title_layout.addStretch()

        self._layout.addWidget(title_bar)

        # --- scroll area ---
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self._layout.addWidget(self._scroll)

        self._placeholder = QLabel("Click near a defect point\nto view details")
        self._placeholder.setObjectName("fieldLabel")
        self._placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._placeholder.setWordWrap(True)
        self._layout.addWidget(self._placeholder)

        self._scroll_widget: QWidget | None = None

    def _on_search(self):
        field = self._field_combo.currentText()
        value = self._value_edit.text().strip()
        if value:
            self.search_requested.emit(field, value)

    def show_defect(self, defect: Defect):
        """Display every defect attribute in a flat list."""
        self._placeholder.hide()
        self._clear_scroll_content()

        content = QWidget()
        grid = QGridLayout(content)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 2)
        grid.setSpacing(0)
        grid.setContentsMargins(4, 0, 4, 0)

        attrs = [
            ("defect_id", str(defect.defect_id)),
            ("event_root_index", str(defect.event_root_index)),
            ("from_channel", str(defect.from_channel)),
            ("channel_defect_id", str(defect.channel_defect_id)),
            ("related_defect_id", str(defect.related_defect_id)),
            ("img_id", str(defect.img_id)),
            ("img_tag", str(defect.img_tag)),
            ("peak_adc", f"{defect.peak_adc:.1f}"),
            ("peak_packet_id", str(defect.peak_packet_id)),
            ("peak_row", f"{defect.peak_row:.1f}"),
            ("peak_col", f"{defect.peak_col:.1f}"),
            ("x_encoder", f"{defect.x_encoder:.1f}"),
            ("w_encoder", f"{defect.w_encoder:.1f}"),
            ("radius", f"{defect.radius:.1f}"),
            ("theta", f"{defect.theta:.4f}"),
            ("x_cor", f"{defect.x_cor:.1f}"),
            ("y_cor", f"{defect.y_cor:.1f}"),
            ("x", f"{defect.x:.1f}"),
            ("y", f"{defect.y:.1f}"),
            ("snr", f"{defect.snr:.1f}"),
            ("defect_area", f"{defect.defect_area:.1f}"),
            ("defect_size", f"{defect.defect_size:.1f}"),
            ("dsize", f"{defect.dsize:.1f}"),
            ("rppm", f"{defect.rppm:.1f}"),
            ("nppm", f"{defect.nppm:.1f}"),
            ("um_size", f"{defect.um_size:.3f}"),
            ("x_size", f"{defect.x_size:.3f}"),
            ("y_size", f"{defect.y_size:.3f}"),
            ("ee", f"{defect.ee:.6f}"),
            ("haze_avg", f"{defect.haze_avg:.1f}"),
            ("defect_tag", str(defect.defect_tag)),
            ("cluster_number", str(defect.cluster_number)),
            ("cluster_area", f"{defect.cluster_area:.1f}"),
            ("cluster_length", f"{defect.cluster_length:.1f}"),
            ("confidence", f"{defect.confidence:.1f}"),
            ("midlevel_bin_number", str(defect.midlevel_bin_number)),
            ("rough_bin_number", str(defect.rough_bin_number)),
            ("fine_bin_number", str(defect.fine_bin_number)),
            ("acc_flag", str(defect.acc_flag)),
            ("cosmic_ray_flag", str(defect.cosmic_ray_flag)),
            ("saturated_flag", str(defect.saturated_flag)),
            ("max_xt_fit", f"{defect.max_xt_fit:.1f}"),
            ("xenc_outer", f"{defect.xenc_outer:.1f}"),
            ("xenc_inner", f"{defect.xenc_inner:.1f}"),
            ("wenc_left", f"{defect.wenc_left:.1f}"),
            ("wenc_right", f"{defect.wenc_right:.1f}"),
        ]

        for row, (name, value) in enumerate(attrs):
            lbl = QLabel(name)
            lbl.setObjectName("fieldLabel")
            val = QLabel(value)
            val.setObjectName("fieldValue")
            val.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextSelectableByMouse
            )
            grid.addWidget(lbl, row, 0)
            grid.addWidget(val, row, 1)

        grid.setRowStretch(len(attrs), 1)

        self._scroll.setWidget(content)
        self._scroll_widget = content

    def clear(self):
        """Reset to placeholder state."""
        self._clear_scroll_content()
        self._placeholder.show()

    def _clear_scroll_content(self):
        if self._scroll_widget is not None:
            self._scroll.takeWidget()
            self._scroll_widget.deleteLater()
            self._scroll_widget = None
