"""Distance scatter chart dialog for coordinate comparison."""

from __future__ import annotations

import math
import numpy as np

from PySide6.QtWidgets import (
    QDialog,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
)
from PySide6.QtCore import Qt

from frontend.xwenc_to_xy import xwenc_to_xy


def compute_distances(defect_array):
    """Compute distance between calculated XY and stored (x,y) for each defect."""
    dists = []
    for d in defect_array:
        cx, cy = xwenc_to_xy(d.x_encoder, d.w_encoder)
        dist = math.hypot(cx - d.x, cy - d.y)
        dists.append(dist)
    return dists


def show_distance_chart(parent, dists, avg):
    """Show scatter plot with statistics in a QDialog."""
    import matplotlib
    matplotlib.use("Qt5Agg")
    from matplotlib import pyplot as plt
    from matplotlib.backends.backend_qt5agg import (
        FigureCanvasQTAgg as FigureCanvas,
    )
    from matplotlib.figure import Figure

    dists = np.array(dists)
    d_min = np.min(dists)
    d_max = np.max(dists)
    d_p2p = d_max - d_min

    fig = Figure(figsize=(7, 4.5))
    ax = fig.add_subplot(111)
    ax.set_title("Defect Distance Scatter", fontsize=11, fontweight="bold")
    ax.set_xlabel("Defect Index")
    ax.set_ylabel("Distance (d)")
    ax.scatter(
        range(len(dists)), dists, s=12, c="#2563a0",
        alpha=0.7, edgecolors="none",
    )
    ax.axhline(y=avg, color="#e67e22", linewidth=1.5,
               linestyle="--", label=f"avg = {avg:.4f}")
    ax.legend(fontsize=9)
    fig.tight_layout()

    canvas = FigureCanvas(fig)

    # stats panel
    stats_widget = QWidget()
    stats_layout = QVBoxLayout(stats_widget)
    stats_layout.setContentsMargins(12, 12, 12, 12)
    stats_layout.setSpacing(6)

    title = QLabel("<b>Statistics</b>")
    stats_layout.addWidget(title)
    for label, value in [
        ("Total", str(len(dists))),
        ("Min", f"{d_min:.4f}"),
        ("Max", f"{d_max:.4f}"),
        ("P2P", f"{d_p2p:.4f}"),
        ("Average", f"{avg:.4f}"),
    ]:
        row = QHBoxLayout()
        row.addWidget(QLabel(label))
        val = QLabel(value)
        val.setStyleSheet("font-family: monospace;")
        row.addWidget(val)
        row.addStretch()
        stats_layout.addLayout(row)
    stats_layout.addStretch()

    # dialog
    dialog = QDialog(parent)
    dialog.setWindowTitle("Defect Distance Statistics")
    dialog.setMinimumSize(800, 400)
    dialog.setAttribute(Qt.WA_DeleteOnClose)

    def _on_close():
        plt.close(fig)

    dialog.finished.connect(_on_close)

    main_layout = QHBoxLayout(dialog)
    main_layout.addWidget(canvas, 3)
    main_layout.addWidget(stats_widget, 1)

    dialog.show()
