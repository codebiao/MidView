"""Global parameters for MidView — populated from my_param.json on load."""

# --- system constants ---
RADIUS_MAX = 150000.0
XENC_MAX = 187500.0
WENC_MAX = 262144.0
R_PIXEL_SIZE = 0.7       # R方向pixel尺寸，单位um/pixel
T_PIXEL_SIZE = 0.7       # T方向pixel尺寸，单位um/pixel

xenc_resolution = RADIUS_MAX / XENC_MAX  # 0.8
xenc_per_pixels = T_PIXEL_SIZE / xenc_resolution
pos = 400  # column index where col value equals current line's xenc

# --- runtime parameters (populated by load_my_param) ---
from backend.models.my_param import MyParam
my_param: MyParam = MyParam()

