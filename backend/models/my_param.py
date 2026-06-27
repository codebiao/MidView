from dataclasses import dataclass, field


@dataclass
class MidlevelSysParam:
    event_merge_rsize: float = 100.0
    event_merge_tsize: float = 100.0
    cosmic_ray_threshold_tsize: float = 10.0
    cosmic_ray_threshold_rsize: float = 5.0
    extended_algo_type: int = 0
    extended_threshold_rect_area: float = 2500.0
    extended_threshold_tsize: float = 100.0
    extended_threshold_rsize: float = 100.0
    extended_hull_filter_enable: int = 1
    img_extended_size: int = 64
    img_lpd_size: int = 32
    img_save_enable: int = 1
    img_save_size: int = 224
    img_save_max_count: int = 1000
    img_save_as_xbit: int = 16
    img_save_count_per_file: int = 1
    radius_filter_enable: int = 0
    radius_filter_threshold: int = 10
    radius_filter_clamp_to_edge_enable: int = 0


@dataclass
class EdsParam:
    notch_wenc: float = 0.0
    offcenter_dist: float = 0.0
    offcenter_wenc: float = 0.0
    notch_theta: float = 0.0
    beta: float = 0.0
    epsilon: float = -0.0
    x_shift: float = 0.0
    y_shift: float = 0.0
    notch_theta_deg: float = 0.0
    beta_deg: float = 0.0
    epsilon_deg: float = -0.0


@dataclass
class XyCalParam:
    rotation: float = 0.10000000149011612
    r_scale: float = 1.0
    x_shift: float = 1.0
    y_shift: float = 2.0
    delta_xl: float = 3.0
    delta_yl: float = 4.0
    x_shift_gt: float = 5.0
    y_shift_gt: float = 6.0
    extra_rotation: float = 0.0
    extra_r_scale: float = 1.0
    extra_x_shift: float = 0.0
    extra_y_shift: float = 0.0
    extra_delta_xl: float = 0.0
    extra_delta_yl: float = 0.0


@dataclass
class MyParam:
    mid_level_dump: int = 1
    dump_dir: str = ""
    img_dir: str = ""
    enable_dual_threshold: int = 0
    dump_dir2: str = ""
    img_dir2: str = ""
    valid_line: int = 2788
    valid_pixels: int = 1500
    scan_stop_radius: float = 50.0
    calc_zone_radius: float = 2500.0
    system_gain: float = 1.0
    xenc_start: float = 2400.0
    notch_theta: float = 0.0
    x_shift: float = 0.0
    y_shift: float = 0.0
    scan_start_radius: float = 150000.0
    frame_tg_size: float = 68.0
    midlevel_sys_param: MidlevelSysParam = field(default_factory=MidlevelSysParam)
    eds_param: EdsParam = field(default_factory=EdsParam)
    xy_cal_param: XyCalParam = field(default_factory=XyCalParam)
