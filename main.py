"""MidView — Interactive Wafer Defect Visualization Tool."""

import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from frontend.main_window import MainWindow


def main():
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setApplicationName("MidView")
    app.setOrganizationName("MidView")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
