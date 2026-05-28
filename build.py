"""Packaging script — builds MidView into a standalone folder using PyInstaller.

Usage:
    python build.py          # build
    python build.py --clean  # clean then build

Output:  dist/MidView/  (self-contained folder, run MidView.exe to launch)
"""

import sys
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist"
NAME = "MidView"
ENTRY = ROOT / "main.py"

# ── hidden imports ─────────────────────────────────────────────────
HIDDEN_IMPORTS = [
    "numpy",
    "numpy.core._methods",
    "numpy.lib.format",
    # matplotlib — lazy-imported in distance_chart_dialog, must be explicit
    "matplotlib",
    "matplotlib.figure",
    "matplotlib.pyplot",
    "matplotlib.backends.backend_qt5agg",
    "matplotlib.backends.backend_agg",
    "matplotlib.backend_bases",
    "PIL",
    "PIL.Image",
    "backend",
    "backend.models",
    "backend.data_load",
    "backend.data_load._helpers",
    "backend.data_load.defect_loader",
    "backend.data_load.event_loader",
    "backend.data_load.packet_raw_meta_loader",
    "backend.data_load.packet8M_loader",
    "backend.data_load.image_meta_loader",
    "frontend",
    "frontend.circular_view",
    "frontend.detail_panel",
    "frontend.event_info_panel",
    "frontend.my_param_dialog",
    "frontend.global_param",
    "frontend.main_window",
    "frontend.packet8m_viewer",
    "frontend.defect_image_viewer",
    "frontend.compare_csv_dialog",
    "frontend.distance_chart_dialog",
    "frontend.theme",
    "frontend.xwenc_to_xy",
]

# ── modules / packages to exclude (not used, but bundled by dependencies) ──
EXCLUDES = [
    # PySide6 heavy modules never used by this app
    "PySide6.QtWebEngineCore",
    "PySide6.QtWebEngineWidgets",
    "PySide6.QtWebChannel",
    "PySide6.QtQml",
    "PySide6.QtQuick",
    "PySide6.QtQuickWidgets",
    "PySide6.QtQuickControls2",
    "PySide6.QtMultimedia",
    "PySide6.QtMultimediaWidgets",
    "PySide6.Qt3DCore",
    "PySide6.Qt3DRender",
    "PySide6.Qt3DInput",
    "PySide6.Qt3DLogic",
    "PySide6.QtSql",
    "PySide6.QtSvg",
    "PySide6.QtSvgWidgets",
    "PySide6.QtTest",
    "PySide6.QtHelp",
    "PySide6.QtXml",
    "PySide6.QtBluetooth",
    "PySide6.QtNfc",
    "PySide6.QtSerialPort",
    "PySide6.QtPositioning",
    "PySide6.QtLocation",
    "PySide6.QtSensors",
    "PySide6.QtTextToSpeech",
    "PySide6.QtWebSockets",
    "PySide6.QtOpenGL",
    "PySide6.QtOpenGLWidgets",
    # unused stdlib packages
    "tkinter",
    "unittest",
    "test",
    "pydoc",
    "distutils",
    "setuptools",
    "pip",
    # matplotlib backends not needed
    "matplotlib.backends.backend_tkagg",
    "matplotlib.backends.backend_wxagg",
    "matplotlib.backends.backend_gtk3agg",
    "matplotlib.backends.backend_gtk4agg",
    "matplotlib.backends.backend_macosx",
    "matplotlib.backends.backend_cairo",
    "matplotlib.backends.backend_pgf",
    "matplotlib.backends.backend_ps",
    "matplotlib.backends.backend_svg",
    "matplotlib.backends.backend_template",
    "matplotlib.backends.backend_webagg",
    "matplotlib.backends.backend_wx",
    # large scientific packages rarely used
    "scipy",
    "pandas",
    "cv2",
]


def clean():
    """Remove previous build artefacts."""
    for d in [DIST, ROOT / "build"]:
        if d.exists():
            shutil.rmtree(d)
    for spec in ROOT.glob("*.spec"):
        spec.unlink()


def build():
    clean()

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onedir",
        "--name", NAME,
        "--distpath", str(DIST),
        "--workpath", str(ROOT / "build"),
        "--specpath", str(ROOT),
        "--noconfirm",
        "--noconsole",
        "--clean",
    ]

    for imp in HIDDEN_IMPORTS:
        cmd += ["--hidden-import", imp]

    for exc in EXCLUDES:
        cmd += ["--exclude-module", exc]

    cmd.append(str(ENTRY))

    print(f"[build] Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=str(ROOT))
    if result.returncode != 0:
        print("[build] PyInstaller failed.", file=sys.stderr)
        sys.exit(result.returncode)

    # copy README into dist folder
    readme = ROOT / "README.md"
    if readme.exists():
        shutil.copy(readme, DIST / NAME / "README.md")

    print(f"\n[build] Done → {DIST / NAME}/")


if __name__ == "__main__":
    if "--clean" in sys.argv:
        clean()
        print("[clean] Build artefacts removed.")
    else:
        build()
