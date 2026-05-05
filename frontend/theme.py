"""Soft light theme stylesheet for PacketView."""

LIGHT_THEME = """
/* === Global === */
QWidget {
    background-color: #f5f4f1;
    color: #3a3a3a;
    font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
    font-size: 13px;
}

/* === Main Window === */
QMainWindow {
    background-color: #f5f4f1;
}

/* === Menu Bar === */
QMenuBar {
    background-color: #eeedea;
    border-bottom: 1px solid #d8d6d2;
    padding: 2px;
}
QMenuBar::item {
    padding: 6px 12px;
    background: transparent;
    border-radius: 4px;
}
QMenuBar::item:selected {
    background-color: #e0dedb;
}
QMenu {
    background-color: #fafaf8;
    border: 1px solid #d8d6d2;
    border-radius: 6px;
    padding: 4px;
}
QMenu::item {
    padding: 8px 32px 8px 16px;
    border-radius: 4px;
}
QMenu::item:selected {
    background-color: #dce8f5;
    color: #2563a0;
}
QMenu::separator {
    height: 1px;
    background: #d8d6d2;
    margin: 4px 12px;
}

/* === Toolbar === */
QToolBar {
    background-color: #eeedea;
    border-bottom: 1px solid #d8d6d2;
    padding: 4px 8px;
    spacing: 6px;
}
QToolBar::separator {
    width: 1px;
    background: #d8d6d2;
    margin: 4px 8px;
}

/* === Push Buttons === */
QPushButton {
    background-color: #e0dedb;
    color: #3a3a3a;
    border: 1px solid #c8c5c1;
    border-radius: 6px;
    padding: 8px 20px;
    font-weight: 500;
}
QPushButton:hover {
    background-color: #d5d3d0;
    border-color: #b0ada9;
}
QPushButton:pressed {
    background-color: #c8c5c1;
}
QPushButton:disabled {
    background-color: #f5f4f1;
    color: #b0ada9;
    border-color: #ddd9d5;
}

/* === Primary Action Button === */
QPushButton#primaryBtn {
    background-color: #2563a0;
    color: #ffffff;
    border-color: #2563a0;
    font-weight: 600;
}
QPushButton#primaryBtn:hover {
    background-color: #1d5080;
    border-color: #1a4570;
}

/* === Line Edit === */
QLineEdit {
    background-color: #fafaf8;
    color: #3a3a3a;
    border: 1px solid #c8c5c1;
    border-radius: 6px;
    padding: 8px 12px;
    selection-background-color: #2563a0;
    selection-color: #ffffff;
}
QLineEdit:focus {
    border-color: #7ab0d0;
    outline: none;
}

/* === Tree View / Table View === */
QTreeView, QTableView {
    background-color: #fafaf8;
    alternate-background-color: #f5f4f1;
    color: #3a3a3a;
    border: 1px solid #d8d6d2;
    border-radius: 6px;
    gridline-color: #e0dedb;
    selection-background-color: #dce8f5;
    selection-color: #3a3a3a;
}
QTreeView::item, QTableView::item {
    padding: 6px 8px;
}
QTreeView::item:hover, QTableView::item:hover {
    background-color: #eeedea;
}
QHeaderView::section {
    background-color: #eeedea;
    color: #555;
    padding: 8px;
    border: none;
    border-right: 1px solid #d8d6d2;
    border-bottom: 2px solid #d8d6d2;
    font-weight: 600;
}

/* === Scroll Bars === */
QScrollBar:vertical {
    background: #f5f4f1;
    width: 10px;
    border-radius: 5px;
    border: 1px solid #e0dedb;
}
QScrollBar::handle:vertical {
    background: #c8c5c1;
    border-radius: 5px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background: #b0ada9;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
QScrollBar:horizontal {
    background: #f5f4f1;
    height: 10px;
    border-radius: 5px;
    border: 1px solid #e0dedb;
}
QScrollBar::handle:horizontal {
    background: #c8c5c1;
    border-radius: 5px;
    min-width: 30px;
}
QScrollBar::handle:horizontal:hover {
    background: #b0ada9;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}

/* === Splitter === */
QSplitter::handle {
    background-color: #d8d6d2;
}
QSplitter::handle:horizontal {
    width: 2px;
}
QSplitter::handle:vertical {
    height: 2px;
}

/* === Status Bar === */
QStatusBar {
    background-color: #eeedea;
    color: #777;
    border-top: 1px solid #d8d6d2;
    padding: 4px 8px;
}

/* === Tool Tips === */
QToolTip {
    background-color: #fafaf8;
    color: #3a3a3a;
    border: 1px solid #d8d6d2;
    border-radius: 4px;
    padding: 4px 8px;
}

/* === Group Box === */
QGroupBox {
    border: 1px solid #d8d6d2;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 16px;
    font-weight: 600;
    color: #555;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 8px;
}

/* === Labels === */
QLabel#sectionTitle {
    color: #2a2a2a;
    font-size: 14px;
    font-weight: 600;
    padding: 4px 0;
}
QLabel#fieldLabel {
    color: #555555;
    font-size: 11px;
    padding: 0;
}
QLabel#fieldValue {
    color: #2a2a2a;
    font-size: 11px;
    padding: 0;
}

/* === Tab Widget === */
QTabWidget::pane {
    border: 1px solid #d8d6d2;
    border-radius: 6px;
    background-color: #fafaf8;
}
QTabBar::tab {
    background-color: #f5f4f1;
    color: #777;
    padding: 8px 16px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    margin-right: 2px;
}
QTabBar::tab:selected {
    background-color: #fafaf8;
    color: #3a3a3a;
    border-bottom: 2px solid #2563a0;
}
QTabBar::tab:hover:!selected {
    color: #555;
}

/* === Spin Box === */
QSpinBox {
    background-color: #fafaf8;
    color: #3a3a3a;
    border: 1px solid #c8c5c1;
    border-radius: 4px;
    padding: 4px 8px;
}
QSpinBox:focus {
    border-color: #7ab0d0;
}
"""
