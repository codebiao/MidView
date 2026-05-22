"""Compare CSV dialog with folder/file panels and diff."""

from __future__ import annotations

import os

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QAbstractItemView,
    QHeaderView,
    QFileDialog,
)
from PySide6.QtCore import Qt


def show_compare_csv_dialog(parent):
    """Open a window to compare CSV files side by side."""
    dialog = QDialog(parent)
    dialog.setWindowTitle("Compare Csv")
    dialog.resize(parent.width() * 4 // 5, parent.height() * 4 // 5)
    dialog.setMinimumSize(800, 500)
    dialog.setAttribute(Qt.WA_DeleteOnClose)

    main_layout = QVBoxLayout(dialog)
    main_layout.setContentsMargins(8, 8, 8, 8)
    main_layout.setSpacing(8)

    # --- top area: left | middle | right ---
    top_area = QHBoxLayout()
    top_area.setSpacing(8)

    def _make_folder_panel():
        """Return (layout, file_list_widget, folder_label)."""
        panel = QVBoxLayout()
        panel.setSpacing(4)
        # folder selector
        folder_row = QHBoxLayout()
        folder_label = QLabel("No folder selected")
        folder_label.setStyleSheet("font-size:11px; color:#555;")
        btn = QPushButton("Select Folder")
        btn.setStyleSheet("padding:2px 8px;")
        folder_row.addWidget(folder_label, 1)
        folder_row.addWidget(btn)
        panel.addLayout(folder_row)
        # file list
        file_list = QListWidget()
        file_list.setStyleSheet("font-size:11px;")
        panel.addWidget(file_list)

        def _on_select_folder():
            path = QFileDialog.getExistingDirectory(dialog, "Select Folder")
            if not path:
                return
            folder_label.setText(path)
            folder_label.setToolTip(path)
            file_list.clear()
            for name in sorted(os.listdir(path)):
                if os.path.isfile(os.path.join(path, name)):
                    it = QListWidgetItem(name)
                    it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    file_list.addItem(it)
            panel._folder_path = path

        btn.clicked.connect(_on_select_folder)
        panel._folder_path = ""
        return panel, file_list

    left_panel, left_list = _make_folder_panel()
    right_panel, right_list = _make_folder_panel()

    # middle comparator table
    middle_panel = QVBoxLayout()
    middle_panel.setSpacing(4)
    mid_label = QLabel("Comparison Pairs")
    mid_label.setStyleSheet("font-weight:700; font-size:12px;")
    mid_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    middle_panel.addWidget(mid_label)

    cmp_table = QTableWidget(0, 3)
    cmp_table.setHorizontalHeaderLabels(["Left File", "Right File", ""])
    cmp_table.horizontalHeader().setSectionResizeMode(
        0, QHeaderView.ResizeMode.Stretch
    )
    cmp_table.horizontalHeader().setSectionResizeMode(
        1, QHeaderView.ResizeMode.Stretch
    )
    cmp_table.horizontalHeader().setSectionResizeMode(
        2, QHeaderView.ResizeMode.Fixed
    )
    cmp_table.setColumnWidth(2, 24)
    cmp_table.setSelectionBehavior(
        QAbstractItemView.SelectionBehavior.SelectRows
    )
    cmp_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    cmp_table.setStyleSheet("font-size:11px;")
    middle_panel.addWidget(cmp_table)

    def _ensure_row_close_btn(r):
        if cmp_table.cellWidget(r, 2) is not None:
            return
        btn = QPushButton("X")
        btn.setFixedSize(20, 20)
        btn.setStyleSheet(
            "QPushButton { background: transparent; border: none;"
            "font-size: 12px; font-weight: 700; color: #999;"
            "padding: 0px; }"
            "QPushButton:hover { color: #dc3545; }"
        )
        btn.clicked.connect(lambda _, row=r: cmp_table.removeRow(row))
        cmp_table.setCellWidget(r, 2, btn)

    # double-click on left list → add to left column of next row or new row
    def _add_left(item):
        name = item.text()
        folder = left_panel._folder_path
        if not folder:
            return
        full = os.path.join(folder, name)
        row = cmp_table.currentRow()
        if row < 0:
            row = cmp_table.rowCount()
            cmp_table.insertRow(row)
            empty_r = QTableWidgetItem("")
            empty_r.setFlags(empty_r.flags() & ~Qt.ItemFlag.ItemIsEditable)
            cmp_table.setItem(row, 1, empty_r)
            _ensure_row_close_btn(row)
        it = QTableWidgetItem(name)
        it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsEditable)
        it.setData(Qt.ItemDataRole.UserRole, full)
        it.setToolTip(full)
        cmp_table.setItem(row, 0, it)

    def _add_right(item):
        name = item.text()
        folder = right_panel._folder_path
        if not folder:
            return
        full = os.path.join(folder, name)
        row = cmp_table.currentRow()
        if row < 0:
            row = cmp_table.rowCount()
            cmp_table.insertRow(row)
            empty_l = QTableWidgetItem("")
            empty_l.setFlags(empty_l.flags() & ~Qt.ItemFlag.ItemIsEditable)
            cmp_table.setItem(row, 0, empty_l)
            _ensure_row_close_btn(row)
        it = QTableWidgetItem(name)
        it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsEditable)
        it.setData(Qt.ItemDataRole.UserRole, full)
        it.setToolTip(full)
        cmp_table.setItem(row, 1, it)

    left_list.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    left_list.setStyleSheet(
        "QListWidget::item:selected { background-color: #b8d4f0; color: #333; }"
    )
    right_list.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    right_list.setStyleSheet(
        "QListWidget::item:selected { background-color: #b8d4f0; color: #333; }"
    )

    left_list.itemDoubleClicked.connect(_add_left)
    right_list.itemDoubleClicked.connect(_add_right)

    top_area.addLayout(left_panel, 1)
    top_area.addLayout(middle_panel, 2)
    top_area.addLayout(right_panel, 1)
    main_layout.addLayout(top_area, 2)

    # --- bottom area: result display ---
    result_text = QTextEdit()
    result_text.setReadOnly(True)
    result_text.setStyleSheet(
        "font-family: monospace; font-size: 11px;"
        "background: #fafaf8; color: #333;"
    )
    main_layout.addWidget(result_text, 1)

    # --- compare button ---
    btn_row = QHBoxLayout()
    btn_row.addStretch()
    compare_btn = QPushButton("Compare")
    compare_btn.setStyleSheet(
        "padding:4px 24px; font-size:13px; font-weight:700;"
        "background: #2563a0; color: #fff;"
    )
    compare_btn.clicked.connect(lambda: _run_comparison())
    btn_row.addWidget(compare_btn)
    main_layout.addLayout(btn_row)

    def _run_comparison():
        result_text.clear()
        for row in range(cmp_table.rowCount()):
            left_item = cmp_table.item(row, 0)
            right_item = cmp_table.item(row, 1)
            if not left_item or not right_item:
                continue
            left_path = left_item.data(Qt.ItemDataRole.UserRole)
            right_path = right_item.data(Qt.ItemDataRole.UserRole)
            if not left_path or not right_path:
                continue
            result_text.append(f"--- Comparing row {row + 1} ---")
            result_text.append(f"  Left:  {os.path.basename(left_path)}")
            result_text.append(f"  Right: {os.path.basename(right_path)}")
            try:
                with open(left_path, "r", encoding="utf-8") as f:
                    left_lines = f.readlines()
                with open(right_path, "r", encoding="utf-8") as f:
                    right_lines = f.readlines()
            except Exception as e:
                result_text.append(f"  Error reading files: {e}")
                continue
            # simple diff
            max_len = max(len(left_lines), len(right_lines))
            diffs = 0
            for i in range(max_len):
                l = left_lines[i].rstrip("\n") if i < len(left_lines) else "<missing>"
                r = right_lines[i].rstrip("\n") if i < len(right_lines) else "<missing>"
                if l != r:
                    diffs += 1
                    result_text.append(f"  Line {i + 1} differs:")
                    result_text.append(f"    L: {l}")
                    result_text.append(f"    R: {r}")
            if diffs == 0:
                result_text.append("  Files are identical.")
            else:
                result_text.append(f"  {diffs} line(s) differ.")
        result_text.append("\nDone.")

    dialog.show()
