# MidView

Interactive visualization tool for wafer defect inspection data.

Displays defect points, event regions, packet boundaries, spiral trajectory, and raw image overlays on a circular wafer map.

## Requirements

| Package    | Minimum Version |
|------------|-----------------|
| Python     | 3.11.0          |
| PySide6    | 6.11.0          |
| NumPy      | 2.4.4           |
| Matplotlib | 3.10.9          |
| Pillow     | 12.2.0          |
| pyqtgraph  | 0.14.0          |

See [requirements.txt](requirements.txt) for pip-installable dependencies.

## Project Structure

```text
MidView/
├── main.py                         # Entry point
├── build.py                        # PyInstaller packaging script
├── backend/
│   ├── models.py                   # Data structures
│   ├── data_load/                  # CSV & binary data loaders
│   └── unpacking8M.py              # 8M binary image parser
├── frontend/
│   ├── main_window.py              # Main application window
│   ├── circular_view.py            # Circular wafer visualization
│   ├── detail_panel.py             # Defect detail panel
│   └── theme.py                    # Light theme stylesheet
└── .claude/                        # Claude Code configuration
```

## Usage

```bash
conda activate MidView
pip install -r requirements.txt
python main.py
```

Click **Load Data** to select a folder containing defects.csv, events.csv, and packet_raw_meta.csv.
