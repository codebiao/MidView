"""Defect image viewer dialog with metadata tables and zoomable image display."""

from __future__ import annotations

import os

import numpy as np
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QGraphicsView,
    QGraphicsScene,
    QGraphicsPixmapItem,
    QAbstractItemView,
    QHeaderView,
    QAbstractScrollArea,
    QFileDialog,
    QApplication,
    QSizePolicy,
    QLayout,
    QMessageBox,
    QMenu,
    QRubberBand,
)
from PySide6.QtCore import Qt, QEvent, QRectF, QPointF
from PySide6.QtGui import (
    QPixmap,
    QImage,
    QPainter,
)

from backend.models import Defect, ImageMeta
from backend.data_load.image_meta_loader import load_image_meta


def show_defect_image_dialog(mw, defect: Defect):
    """Show the defect image viewer dialog for a given defect."""
    if not mw._data_folder:
        return

    mw._ensure_img_meta_loaded()

    idx = defect.img_id - 1
    if idx < 0 or idx >= len(mw._img_meta_array):
        QMessageBox.warning(
            mw,
            "Not Found",
            f"ImageMeta index {idx} (img_id={defect.img_id}) "
            f"out of range (loaded {len(mw._img_meta_array)} metas).",
        )
        return

    img_meta = mw._img_meta_array[idx]

    # --- build dialog ---
    dialog = QDialog(mw)
    dialog.setWindowTitle(
        f"Defect #{defect.defect_id}  —  Image #{img_meta.img_id}"
    )
    dialog.setMinimumSize(780, 600)
    dialog.setAttribute(Qt.WA_DeleteOnClose)

    main_layout = QVBoxLayout(dialog)

    # ===== ImageMeta table (1 data row, value-only) =====
    im_cols = [
        "index", "img_id", "is_valid", "scale", "proc_id", "file_name",
        "pos", "angle_deg", "overlap_prev", "overlap_next",
        "tag", "packet_count",
    ]
    im_values = [
        str(idx), str(img_meta.img_id), str(img_meta.is_valid),
        f"{img_meta.scale:.3f}", str(img_meta.proc_id),
        img_meta.file_name, str(img_meta.pos),
        f"{img_meta.angle_deg:.3f}", str(img_meta.overlap_pixels_prev),
        str(img_meta.overlap_pixels_next), str(img_meta.tag),
        str(img_meta.packet_array_count),
    ]

    im_table = QTableWidget(1, len(im_cols))
    im_table.setHorizontalHeaderLabels(im_cols)
    im_table.verticalHeader().setVisible(False)
    for j, val in enumerate(im_values):
        item = QTableWidgetItem(val)
        item.setFlags(Qt.ItemIsEnabled)
        im_table.setItem(0, j, item)
    im_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
    im_table.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)
    im_table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    im_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
    main_layout.addWidget(im_table)

    # small gap between tables
    main_layout.addSpacing(4)

    # ===== PacketMeta table =====
    pk_cols = [
        "pkg_idx", "pkt_id", "proc_id", "center",
        "pkg_row_start", "pkg_row_end",
        "pkg_col_start", "pkg_col_end",
        "img_row_start", "img_col_start",
        "img_row_count", "img_col_count",
    ]
    n_pkts = len(img_meta.packet_array)
    pk_table = QTableWidget(n_pkts, len(pk_cols))
    pk_table.setHorizontalHeaderLabels(pk_cols)

    vh_labels = [
        f"Pkt[{img_meta.packet_array[k].pkg_index}]"
        for k in range(n_pkts)
    ]
    pk_table.setVerticalHeaderLabels(vh_labels)

    for k, p in enumerate(img_meta.packet_array):
        vals = [
            str(p.pkg_index), str(p.packet_id),
            str(p.from_proc_id), str(p.is_center),
            str(p.pkg_row_start), str(p.pkg_row_end),
            str(p.pkg_col_start), str(p.pkg_col_end),
            str(p.img_row_start), str(p.img_col_start),
            str(p.img_row_count), str(p.img_col_count),
        ]
        for j, val in enumerate(vals):
            item = QTableWidgetItem(val)
            item.setFlags(Qt.ItemIsEnabled)
            pk_table.setItem(k, j, item)

    pk_table.horizontalHeader().setSectionResizeMode(
        QHeaderView.ResizeToContents
    )
    pk_table.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)
    pk_table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    pk_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
    main_layout.addWidget(pk_table)

    # ===== image section =====
    IMG_SIZE = 224

    # info labels created early — added to layout later
    info_left = QLabel("0×0 pixels, 0-bit; 0K")
    info_left.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
    info_left.setStyleSheet(
        "padding:1px 0px 1px 2px; background:transparent; font-family:monospace;"
    )
    info_right = QLabel("x=0, y=0, value=0")
    info_right.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
    info_right.setStyleSheet(
        "padding:1px 2px 1px 0px; background:transparent; color:#333; font-family:monospace;"
    )

    # QGraphicsView for image — same approach as main defect canvas
    scene = QGraphicsScene()
    gv = QGraphicsView(scene)
    gv.setFixedSize(IMG_SIZE + 4, IMG_SIZE + 4)
    gv.setStyleSheet(
        "background-color: #e8e8e8; border:1px solid #aaa; border-top:none;"
    )
    gv.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    gv.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    gv.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
    gv.setTransformationAnchor(
        QGraphicsView.ViewportAnchor.AnchorUnderMouse
    )
    gv.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
    gv.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    gv.setViewportUpdateMode(
        QGraphicsView.ViewportUpdateMode.FullViewportUpdate
    )

    pixmap_item = QGraphicsPixmapItem()
    pixmap_item.setTransformationMode(
        Qt.TransformationMode.SmoothTransformation
    )
    scene.addItem(pixmap_item)

    # pixel tracking state
    source_image: QImage | None = None
    source_data: np.ndarray | None = None
    _display_norm_buffer: np.ndarray | None = None  # keep alive for QImage
    view_image_path: str = ""
    view_file_size: int = 0
    display_bit_depth: int = 16

    def _load_source_image(path: str):
        nonlocal source_image, source_data
        reader = QImage(path)
        if reader.isNull():
            return False
        fmt = reader.format()
        if fmt in (QImage.Format.Format_Grayscale16, QImage.Format.Format_Grayscale8):
            source_image = reader.copy()
        else:
            source_image = reader.convertToFormat(QImage.Format.Format_Grayscale16)
        w, h = source_image.width(), source_image.height()
        if source_image.depth() == 16:
            ptr = source_image.constBits()
            arr = np.frombuffer(ptr, dtype=np.uint16, count=w * h)
            source_data = arr.reshape((h, w)).copy()
        else:
            ptr = source_image.constBits()
            arr = np.frombuffer(ptr, dtype=np.uint8, count=w * h)
            source_data = arr.reshape((h, w)).astype(np.uint16).copy()
        return True

    def _build_display_qimage():
        nonlocal _display_norm_buffer
        if source_data is None:
            return QImage()
        data_f = source_data.astype(np.float64)
        d_min, d_max = data_f.min(), data_f.max()
        if d_max > d_min:
            _display_norm_buffer = (
                (data_f - d_min) / (d_max - d_min) * 255
            ).astype(np.uint8)
        else:
            _display_norm_buffer = np.zeros_like(data_f, dtype=np.uint8)
        h, w = _display_norm_buffer.shape
        return QImage(
            _display_norm_buffer.data, w, h, w,
            QImage.Format.Format_Grayscale8,
        )

    def _refresh_image():
        if not view_image_path or not os.path.isfile(view_image_path):
            pixmap_item.setPixmap(QPixmap())
            info_left.setText("0×0 pixels, 0-bit; 0K")
            info_right.setText("x=0, y=0, value=0")
            return
        if not _load_source_image(view_image_path):
            pixmap_item.setPixmap(QPixmap())
            return

        disp_img = _build_display_qimage()
        pixmap = QPixmap.fromImage(disp_img)
        pixmap_item.setPixmap(pixmap)
        scene.setSceneRect(QRectF(pixmap.rect()))

        w, h = source_image.width(), source_image.height()
        depth_label = "16-bit" if display_bit_depth == 16 else "8-bit"
        kb = view_file_size // 1024 if view_file_size else 0
        info_left.setText(f"{w}×{h} pixels; {depth_label}; {kb}K")

    def _zoom_to_fit():
        if not view_image_path:
            return
        if source_image is None:
            _refresh_image()
        if source_image is None:
            return
        gv.fitInView(scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    # rubber-band zoom state
    _rubber_band: QRubberBand | None = None
    _rubber_origin: QPointF | None = None
    _suppress_ctx_menu = False

    # context menu
    gv.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

    def _on_context_menu(pos):
        nonlocal _suppress_ctx_menu
        if _suppress_ctx_menu:
            _suppress_ctx_menu = False
            return
        menu = QMenu(gv)
        menu.addAction("Fit View", _zoom_to_fit)
        menu.exec(gv.mapToGlobal(pos))

    gv.customContextMenuRequested.connect(_on_context_menu)

    # event filter for pixel tracking + rubber-band zoom
    gv.viewport().setMouseTracking(True)
    info_right_default = "x=0, y=0, value=0"

    def _image_event_filter(obj, event):
        nonlocal _rubber_band, _rubber_origin, _suppress_ctx_menu
        t = event.type()
        if t == QEvent.Type.MouseButtonPress:
            if event.button() == Qt.MouseButton.RightButton:
                _rubber_origin = event.pos()
                if _rubber_band is None:
                    _rubber_band = QRubberBand(QRubberBand.Shape.Rectangle, gv)
                _rubber_band.setGeometry(event.pos().x(), event.pos().y(), 0, 0)
                _rubber_band.show()
                return True
        elif t == QEvent.Type.MouseMove:
            if _rubber_band is not None and _rubber_band.isVisible() and _rubber_origin is not None:
                x = min(_rubber_origin.x(), event.pos().x())
                y = min(_rubber_origin.y(), event.pos().y())
                w = abs(event.pos().x() - _rubber_origin.x())
                h = abs(event.pos().y() - _rubber_origin.y())
                _rubber_band.setGeometry(x, y, w, h)
                return True
            if source_data is not None and source_image is not None:
                sp = gv.mapToScene(event.pos())
                ix = int(sp.x())
                iy = int(sp.y())
                if (
                    0 <= ix < source_image.width()
                    and 0 <= iy < source_image.height()
                ):
                    val = int(source_data[iy, ix])
                    if display_bit_depth == 8:
                        val = val >> 8
                    info_right.setText(
                        f"x={ix}, y={iy}, value={val}"
                    )
                else:
                    info_right.setText(info_right_default)
            else:
                info_right.setText(info_right_default)
        elif t == QEvent.Type.MouseButtonRelease:
            if event.button() == Qt.MouseButton.RightButton:
                if _rubber_band is not None:
                    _rubber_band.hide()
                    rect = _rubber_band.geometry()
                    _rubber_origin = None
                    if rect.width() > 4 and rect.height() > 4:
                        _suppress_ctx_menu = True
                        top_left = gv.mapToScene(rect.topLeft())
                        bottom_right = gv.mapToScene(rect.bottomRight())
                        scene_rect = QRectF(top_left, bottom_right)
                        gv.fitInView(scene_rect, Qt.AspectRatioMode.KeepAspectRatio)
                return False
        elif t == QEvent.Type.Leave:
            info_right.setText(info_right_default)
        elif t == QEvent.Type.Wheel:
            delta = event.angleDelta().y()
            factor = 1.25 if delta > 0 else 0.8
            gv.scale(factor, factor)
            return True
        return False

    gv.viewport().installEventFilter(mw)
    dialog._img_event_filter = _image_event_filter

    if not hasattr(mw, "_dialog_filters"):
        mw._dialog_filters = {}
        _orig = mw.eventFilter

        def _global_filter(obj, event):
            cb = mw._dialog_filters.get(obj)
            if cb is not None:
                return cb(obj, event)
            if _orig:
                return _orig(obj, event)
            return False

        mw.eventFilter = _global_filter

    mw._dialog_filters[gv.viewport()] = _image_event_filter

    def _browse():
        nonlocal view_image_path, view_file_size
        path, _ = QFileDialog.getOpenFileName(
            dialog,
            "Select Image File",
            img_folder if os.path.isdir(img_folder) else os.getcwd(),
            "Images (*.png *.jpg *.jpeg *.bmp *.tiff *.tif);;All (*.*)",
        )
        if path:
            view_image_path = path
            view_file_size = os.path.getsize(path)
            QApplication.processEvents()
            _zoom_to_fit()

    # load initial image
    img_folder = os.path.join(mw._data_folder, "defect_img")
    auto_path = os.path.join(img_folder, img_meta.file_name)
    if os.path.isfile(auto_path):
        view_image_path = auto_path
        view_file_size = os.path.getsize(auto_path)
    else:
        view_image_path = ""
        view_file_size = 0

    # --- spacing before controls ---
    main_layout.addSpacing(4)

    # --- image controls row ---
    ctrl_layout = QHBoxLayout()

    load_btn = QPushButton("Load Image")
    load_btn.setStyleSheet(
        "QPushButton { padding:2px 6px; }"
    )
    load_btn.setSizePolicy(
        QSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
    )
    load_btn.clicked.connect(_browse)
    ctrl_layout.addWidget(load_btn)

    ctrl_layout.addStretch()
    main_layout.addLayout(ctrl_layout)

    # --- info bar (seamless with canvas) ---
    info_bar = QHBoxLayout()
    info_bar.setContentsMargins(0, 0, 0, 0)
    info_bar.setSpacing(0)
    info_bar.addWidget(info_left)
    info_bar.addWidget(info_right)

    info_frame = QFrame()
    info_frame.setLayout(info_bar)
    info_frame.setFixedWidth(IMG_SIZE + 4)
    info_frame.setStyleSheet(
        "QFrame { background:transparent; border:none; }"
    )
    main_layout.addWidget(info_frame)

    # image display area
    main_layout.addWidget(gv)
    main_layout.setSpacing(0)

    # prevent window resizing
    dialog.layout().setSizeConstraint(
        QLayout.SizeConstraint.SetFixedSize
    )

    dialog.show()

    # flush pending events so dialog is fully visible
    QApplication.processEvents()
    _zoom_to_fit()
