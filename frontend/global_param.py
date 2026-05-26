"""Global parameters for MidView."""

RADIUS_MAX = 150000.0
XENC_MAX = 187500.0
WENC_MAX = 262144.0
R_PIXEL_SIZE = 0.7       # R向pixels的大小，单位um/pixel
T_PIXEL_SIZE = 0.7       # T向pixels的大小，单位um/pixel

xenc_resolution = RADIUS_MAX / XENC_MAX
xenc_start = 0.0          # 扫描结束的半径
scan_start_radius = 0.0   # 扫描开始的半径，单位um
