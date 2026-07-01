from dataclasses import dataclass


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
    group_id: int
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
    from_proc_id: int = 0
    proc_id: int = 0
    signal_type: int = 0
    r_size: float = 0.0
    t_size: float = 0.0
    median_r_size: float = 0.0
    median_t_size: float = 0.0
    r_cluster_size: float = 0.0
    t_cluster_size: float = 0.0

