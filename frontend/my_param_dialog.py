"""MyParam viewer dialog."""

from __future__ import annotations

import dataclasses

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QGridLayout,
    QScrollArea,
    QLabel,
    QWidget,
    QFrame,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QFontMetrics

from backend.models.my_param import MyParam

ROW_STYLE = "font-family: monospace; font-size: 11px; color: #2563a0; background: transparent;"
SECTION_TITLE = (
    "font-family: monospace; font-size: 11px; font-weight: 700;"
    "color: #1a4a7a; background: transparent; padding: 4px 0px 0px 0px;"
)


def show_my_param_dialog(parent, my_param: MyParam):
    """Show MyParam struct contents in a dialog."""
    if my_param is None:
        return

    dialog = QDialog(parent)
    dialog.setWindowTitle("MyParam")
    dialog.setAttribute(Qt.WA_DeleteOnClose)
    dialog.setMinimumSize(500, 400)

    outer = QVBoxLayout(dialog)
    outer.setContentsMargins(8, 8, 8, 8)
    outer.setSpacing(4)

    rows: list[tuple[str, str, bool]] = []
    for f in dataclasses.fields(my_param):
        val = getattr(my_param, f.name)
        if hasattr(val, "__dataclass_fields__"):
            rows.append((f.name, "", True))
            for sf in dataclasses.fields(val):
                rows.append((sf.name, str(getattr(val, sf.name)), False))
        else:
            rows.append((f.name, str(val), False))

    _font = QFont("monospace", 11)
    _fm = QFontMetrics(_font)
    _label_w = max((_fm.horizontalAdvance(r[0]) for r in rows), default=0) + 12

    grid_widget = QWidget()
    grid = QGridLayout(grid_widget)
    grid.setContentsMargins(8, 4, 8, 4)
    grid.setHorizontalSpacing(3)
    grid.setVerticalSpacing(1)

    r = 0
    for label, value, is_title in rows:
        lbl = QLabel(label)
        val = QLabel(value)
        if is_title:
            lbl.setStyleSheet(SECTION_TITLE)
        else:
            lbl.setStyleSheet(ROW_STYLE)
            val.setStyleSheet(ROW_STYLE)
            lbl.setFixedWidth(_label_w)
            val.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        grid.addWidget(lbl, r, 0)
        grid.addWidget(val, r, 1)
        r += 1
    grid.setRowStretch(r, 1)

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setWidget(grid_widget)
    outer.addWidget(scroll, 1)

    dialog.show()
