"""Coordinate conversion utilities for wafer visualization."""

import math

RADIUS_MAX = 150000.0
WENC_MAX = 262144.0
XENC_MAX = 187500.0
XENC_START = 2400.0
R_PIXEL_SIZE = 0.7      # R向pixels的大小，单位um/pixel
T_PIXEL_SIZE = 0.7      # T向pixels的大小，单位um/pixel

def xwenc_to_xy(xenc: float, wenc: float) -> tuple[float, float]:
    angle = 2.0 * math.pi * wenc / WENC_MAX
    r = RADIUS_MAX * (XENC_MAX - xenc) / (XENC_MAX - XENC_START)
    x = r * math.cos(angle)
    y = r * math.sin(angle)
    return x, y