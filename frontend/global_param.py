"""Global parameters for MidView — populated from my_param.json on load."""

# --- system constants ---
RADIUS_MAX = 150000.0
XENC_MAX = 187500.0
WENC_MAX = 262144.0
R_PIXEL_SIZE = 0.7       # R方向pixel尺寸，单位um/pixel
T_PIXEL_SIZE = 0.7       # T方向pixel尺寸，单位um/pixel

xenc_resolution = RADIUS_MAX / XENC_MAX

# --- my_param top-level fields ---
mid_level_dump = 1
out_path = ""
enable_double_threshold = 0
valid_line = 2431
valid_pixels = 1712
scan_stop_radius = 140000.0
calc_zone_radius = 500.0
system_gain = 0.025792844593524933
xenc_start = 2399.0
notch_theta = 3.140000104904175
x_shift = 60.77000045776367
y_shift = 34.91999816894531
scan_start_radius = 148100.0
frame_tg_size = 143.0
camera_pixel_start = 388

# --- midlevel_sys_param ---
midlevel_sys_param = {
    "event_merge_rsize": 5.0,
    "event_merge_tsize": 5.0,
    "cosmic_ray_threshold_tsize": 5.0,
    "cosmic_ray_threshold_rsize": 1.0,
    "calc_final_size_enable": 0,
    "extended_algo_type": 0,
    "extended_threshold_rect_area": 2500.0,
    "extended_threshold_tsize": 100.0,
    "extended_threshold_rsize": 100.0,
    "img_size": 224,
    "img_save_enable": 1,
    "img_save_max_count": 1000,
    "img_save_as_xbit": 16,
    "img_save_count_per_file": 1,
    "radius_filter_enable": 0,
    "radius_filter_threshold": 10,
    "radius_filter_clamp_to_edge_enable": 0,
}

# --- xy_cal_param ---
xy_cal_param = {
    "rotation": 0.0,
    "r_scale": 1.0,
    "x_shift": 0.0,
    "y_shift": 0.0,
    "delta_xl": 0.0,
    "delta_yl": 0.0,
    "x_shift_gt": 0.0,
    "y_shift_gt": 0.0,
}
