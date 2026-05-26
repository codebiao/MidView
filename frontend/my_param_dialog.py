"""MyParam JSON viewer dialog."""

from __future__ import annotations

import json

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QGridLayout,
    QTextEdit,
    QLabel,
    QWidget,
)
from PySide6.QtCore import Qt

from frontend import global_param as _cfg


def show_my_param_dialog(parent, my_param: dict):
    """Show my_param.json contents in a dialog."""
    if my_param is None:
        return
    content = json.dumps(my_param, indent=4, ensure_ascii=False)
    lines = content.split("\n")
    line_count = len(lines)
    max_line_len = max(len(line) for line in lines)

    dialog = QDialog(parent)
    dialog.setWindowTitle("MyParam")
    dialog.setAttribute(Qt.WA_DeleteOnClose)

    layout = QVBoxLayout(dialog)
    layout.setContentsMargins(8, 8, 8, 8)
    layout.setSpacing(6)

    text = QTextEdit()
    text.setReadOnly(True)
    text.setStyleSheet(
        "font-family: monospace; font-size: 12px;"
        "background: #fafaf8; color: #333;"
    )
    text.setPlainText(content)

    fm = text.fontMetrics()
    char_w = fm.horizontalAdvance(" ")
    line_h = fm.lineSpacing() + 2
    text.setMinimumSize(
        max(480, int(char_w * max_line_len) + 32),
        int(line_h * line_count) + 16,
    )
    layout.addWidget(text)

    info_frame = QWidget()
    info_frame.setStyleSheet(
        "background: #e8f0f8; border-radius: 4px;"
    )
    info_grid = QGridLayout(info_frame)
    info_grid.setContentsMargins(8, 4, 8, 4)
    info_grid.setHorizontalSpacing(5)
    info_grid.setVerticalSpacing(2)

    row_style = "font-family: monospace; font-size: 11px; color: #2563a0; background: transparent;"
    from PySide6.QtGui import QFont, QFontMetrics
    _font = QFont("monospace", 11)
    _fm = QFontMetrics(_font)
    items = [
        ("xenc_start", f"{_cfg.xenc_start:.1f}"),
        ("scan_start_radius", f"{_cfg.scan_start_radius:.1f}"),
    ]
    _label_w = max(_fm.horizontalAdvance(t) for t, _ in items) + 6
    for r, (label_text, value_text) in enumerate(items):
        lbl = QLabel(label_text)
        lbl.setStyleSheet(row_style)
        lbl.setFixedWidth(_label_w)
        val = QLabel(value_text)
        val.setStyleSheet(row_style)
        info_grid.addWidget(lbl, r, 0)
        info_grid.addWidget(val, r, 1)

    layout.addWidget(info_frame)

    dialog.adjustSize()
    dialog.show()
