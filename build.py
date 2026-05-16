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
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
    "numpy",
    "numpy.core._methods",
    "numpy.lib.format",
    "matplotlib",
    "matplotlib.backends.backend_qt5agg",
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
    "frontend.theme",
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

    # hidden imports
    for imp in HIDDEN_IMPORTS:
        cmd += ["--hidden-import", imp]

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
