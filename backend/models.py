"""Data models for MidView. Struct names use PascalCase per project convention."""

from dataclasses import dataclass, field
from typing import Optional
import numpy as np


@dataclass
class Defect:
    index: int
    parent: int
    next: int
    tail: int
    count: int
    status: int
    track_id: int
    source_type: int
    defect_id: int
    event_root_index: int
    from_channel: int
    channel_defect_id: int
    related_defect_id: int
    img_id: int
    img_tag: int
    peak_adc: float
    peak_packet_id: int
    peak_row: float
    peak_col: float
    x_encoder: float
    w_encoder: float
    radius: float
    theta: float
    x_cor: float
    y_cor: float
    x: float
    y: float
    snr: float
    defect_area: float
    defect_size: float
    dsize: float
    rppm: float
    nppm: float
    um_size: float
    x_size: float
    y_size: float
    ee: float
    haze_avg: float
    defect_tag: int
    cluster_number: int
    cluster_area: float
    cluster_length: float
    confidence: float
    midlevel_bin_number: int
    rough_bin_number: int
    fine_bin_number: int
    acc_flag: int
    cosmic_ray_flag: int
    saturated_flag: int
    max_xt_fit: float
    xenc_outer: float
    xenc_inner: float
    wenc_left: float
    wenc_right: float


@dataclass
class Event:
    index: int
    this_ptr: int
    parent: int
    next: int
    prev: int
    next_track: int
    prev_track: int
    track_root: int
    count: int
    track_count: int
    track_node_count: int
    status: int
    track_id: int
    event_id: int
    proc_id: int
    packet_id: int
    peak_adc: float
    peak_row: float
    peak_col: float
    x_encoder: float
    w_encoder: float
    radius: float
    theta: float
    x_cor: float
    y_cor: float
    x: float
    y: float
    snr: float
    ee: float
    ee_is_fitted: int
    xenc_merge_count: float
    wenc_merge_count: float
    wenc_per_um: float
    box_width: float
    box_height: float
    xenc_outer: float
    xenc_inner: float
    wenc_left: float
    wenc_right: float
    acc_flag: int
    cosmic_ray_flag: int
    saturated_flag: int
    pixel_sindex: int
    pixel_eindex: int


@dataclass
class PacketRawMeta:
    packet_id: int
    from_proc_id: int
    track_id_start: int
    track_id_end: int
    addr: int
    size: int
    xenc_outer: float
    xenc_inner: float
    wenc_left: float
    wenc_right: float


@dataclass
class PacketImage:
    packet_id: int
    head: dict
    data: np.ndarray
    footer: dict


@dataclass
class PacketMeta:
    pkg_index: int
    packet_id: int
    from_proc_id: int
    is_center: int = 0
    pkg_row_start: float = 0.0
    pkg_row_end: float = 0.0
    pkg_col_start: float = 0.0
    pkg_col_end: float = 0.0
    img_row_start: float = 0.0
    img_col_start: float = 0.0
    img_row_count: float = 0.0
    img_col_count: float = 0.0


@dataclass
class ImageMeta:
    img_id: int = -1
    is_valid: int = 0
    scale: float = 1.0
    proc_id: int = -1
    file_name: str = ""
    pos: int = 0
    angle_deg: float = 0.0
    overlap_pixels_prev: int = 0
    overlap_pixels_next: int = 0
    tag: int = 0
    packet_array: list[PacketMeta] = field(default_factory=list)
    packet_array_count: int = 0
