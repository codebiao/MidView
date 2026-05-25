"""MyParam JSON viewer dialog."""

from __future__ import annotations

import json

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QTextEdit,
)
from PySide6.QtCore import Qt


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
    text.setMaximumHeight(int(line_h * line_count) + 16)
    layout.addWidget(text)

    dialog.adjustSize()
    dialog.show()
