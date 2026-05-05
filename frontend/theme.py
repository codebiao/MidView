"""Light theme stylesheet for PacketView."""

LIGHT_THEME = """
/* === Global === */
QWidget {
    background-color: #f8f9fa;
    color: #212529;
    font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
    font-size: 13px;
}

/* === Main Window === */
QMainWindow {
    background-color: #f8f9fa;
}

/* === Menu Bar === */
QMenuBar {
    background-color: #ffffff;
    border-bottom: 1px solid #dee2e6;
    padding: 2px;
}
QMenuBar::item {
    padding: 6px 12px;
    background: transparent;
    border-radius: 4px;
}
QMenuBar::item:selected {
    background-color: #e9ecef;
}
QMenu {
    background-color: #ffffff;
    border: 1px solid #dee2e6;
    border-radius: 6px;
    padding: 4px;
}
QMenu::item {
    padding: 8px 32px 8px 16px;
    border-radius: 4px;
}
QMenu::item:selected {
    background-color: #e7f1ff;
    color: #0d6efd;
}
QMenu::separator {
    height: 1px;
    background: #dee2e6;
    margin: 4px 12px;
}

/* === Toolbar === */
QToolBar {
    background-color: #ffffff;
    border-bottom: 1px solid #dee2e6;
    padding: 4px 8px;
    spacing: 6px;
}
QToolBar::separator {
    width: 1px;
    background: #dee2e6;
    margin: 4px 8px;
}

/* === Push Buttons === */
QPushButton {
    background-color: #e9ecef;
    color: #212529;
    border: 1px solid #ced4da;
    border-radius: 6px;
    padding: 8px 20px;
    font-weight: 500;
}
QPushButton:hover {
    background-color: #dee2e6;
    border-color: #adb5bd;
}
QPushButton:pressed {
    background-color: #ced4da;
}
QPushButton:disabled {
    background-color: #f8f9fa;
    color: #adb5bd;
    border-color: #e9ecef;
}

/* === Primary Action Button === */
QPushButton#primaryBtn {
    background-color: #0d6efd;
    color: #ffffff;
    border-color: #0d6efd;
    font-weight: 600;
}
QPushButton#primaryBtn:hover {
    background-color: #0b5ed7;
    border-color: #0a58ca;
}

/* === Line Edit === */
QLineEdit {
    background-color: #ffffff;
    color: #212529;
    border: 1px solid #ced4da;
    border-radius: 6px;
    padding: 8px 12px;
    selection-background-color: #0d6efd;
    selection-color: #ffffff;
}
QLineEdit:focus {
    border-color: #86b7fe;
    outline: none;
}

/* === Tree View / Table View === */
QTreeView, QTableView {
    background-color: #ffffff;
    alternate-background-color: #f8f9fa;
    color: #212529;
    border: 1px solid #dee2e6;
    border-radius: 6px;
    gridline-color: #e9ecef;
    selection-background-color: #e7f1ff;
    selection-color: #212529;
}
QTreeView::item, QTableView::item {
    padding: 6px 8px;
}
QTreeView::item:hover, QTableView::item:hover {
    background-color: #f1f3f5;
}
QHeaderView::section {
    background-color: #f8f9fa;
    color: #495057;
    padding: 8px;
    border: none;
    border-right: 1px solid #dee2e6;
    border-bottom: 2px solid #dee2e6;
    font-weight: 600;
}

/* === Scroll Bars === */
QScrollBar:vertical {
    background: #f8f9fa;
    width: 10px;
    border-radius: 5px;
    border: 1px solid #e9ecef;
}
QScrollBar::handle:vertical {
    background: #ced4da;
    border-radius: 5px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background: #adb5bd;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
QScrollBar:horizontal {
    background: #f8f9fa;
    height: 10px;
    border-radius: 5px;
    border: 1px solid #e9ecef;
}
QScrollBar::handle:horizontal {
    background: #ced4da;
    border-radius: 5px;
    min-width: 30px;
}
QScrollBar::handle:horizontal:hover {
    background: #adb5bd;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}

/* === Splitter === */
QSplitter::handle {
    background-color: #dee2e6;
}
QSplitter::handle:horizontal {
    width: 2px;
}
QSplitter::handle:vertical {
    height: 2px;
}

/* === Status Bar === */
QStatusBar {
    background-color: #ffffff;
    color: #6c757d;
    border-top: 1px solid #dee2e6;
    padding: 4px 8px;
}

/* === Tool Tips === */
QToolTip {
    background-color: #ffffff;
    color: #212529;
    border: 1px solid #dee2e6;
    border-radius: 4px;
    padding: 4px 8px;
}

/* === Group Box === */
QGroupBox {
    border: 1px solid #dee2e6;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 16px;
    font-weight: 600;
    color: #495057;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 8px;
}

/* === Labels === */
QLabel#sectionTitle {
    color: #0d6efd;
    font-size: 14px;
    font-weight: 600;
    padding: 4px 0;
}
QLabel#fieldLabel {
    color: #6c757d;
    font-size: 11px;
    padding: 1px 0;
}
QLabel#fieldValue {
    color: #212529;
    font-size: 11px;
    padding: 1px 0;
}

/* === Tab Widget === */
QTabWidget::pane {
    border: 1px solid #dee2e6;
    border-radius: 6px;
    background-color: #ffffff;
}
QTabBar::tab {
    background-color: #f8f9fa;
    color: #6c757d;
    padding: 8px 16px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    margin-right: 2px;
}
QTabBar::tab:selected {
    background-color: #ffffff;
    color: #212529;
    border-bottom: 2px solid #0d6efd;
}
QTabBar::tab:hover:!selected {
    color: #495057;
}

/* === Spin Box === */
QSpinBox {
    background-color: #ffffff;
    color: #212529;
    border: 1px solid #ced4da;
    border-radius: 4px;
    padding: 4px 8px;
}
QSpinBox:focus {
    border-color: #86b7fe;
}
"""
