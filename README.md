# MidView

Interactive visualization tool for wafer defect inspection data.

Displays defect points, event regions, packet boundaries, and raw image overlays on a circular wafer map with Archimedean spiral reference trajectory.

## Tech Stack

- **UI Framework**: PySide6
- **Plotting**: PyQtGraph
- **Data Processing**: NumPy, Pandas

## Project Structure

```
MidView/
├── main.py                 # Entry point
├── backend/
│   ├── models.py           # Data structures
│   ├── data_load/          # CSV & binary data loaders
│   └── unpacking8M.py      # 8M binary image parser
├── frontend/
│   ├── main_window.py      # Main application window
│   ├── circular_view.py    # Circular wafer visualization
│   ├── detail_panel.py     # Defect detail panel
│   └── theme.py            # Dark theme stylesheet
└── utils/                  # Standalone utilities
```

## Usage

```bash
conda activate MidView
pip install -r requirements.txt
python main.py
```

Click "Load Data" to select a folder containing defects.csv, events.csv, and packet_raw_meta.csv.
