"""Coordinate conversion utilities for wafer visualization."""

import math

RADIUS_MAX = 150000.0
XENC_MAX = 187500.0
WENC_MAX = 262144.0
R_PIXEL_SIZE = 0.7       # R向pixels的大小，单位um/pixel
T_PIXEL_SIZE = 0.7       # T向pixels的大小，单位um/pixel

xenc_resolution = RADIUS_MAX / XENC_MAX
xenc_start = 63024.0     # 扫描结束的半径，
scan_start_radius = 99600.0  # 扫描开始的半径，单位um


def xenc_to_radius(xenc: float) -> float:
    radius = scan_start_radius - (xenc - xenc_start) * xenc_resolution
    return radius if radius > 0.0 else 10.0


def wenc_to_angle(wenc: float) -> float:
    theta = -((wenc / WENC_MAX) * 2.0 * math.pi)
    return theta


def trans_xy_r2w(x_cor: float, y_cor: float, notch_theta: float, x_shift: float, y_shift: float) -> tuple[float, float]:
    # shift
    x_cor = x_cor + x_shift
    y_cor = y_cor + y_shift

    # rotation
    sin_theta = math.sin(notch_theta - math.pi / 2.0)
    cos_theta = math.cos(notch_theta - math.pi / 2.0)
    x_out = x_cor * cos_theta - y_cor * sin_theta
    y_out = x_cor * sin_theta + y_cor * cos_theta
    return x_out, y_out


def xwenc_to_xy(xenc: float, wenc: float) -> tuple[float, float]:
    # get cor
    radius = xenc_to_radius(xenc)
    theta = wenc_to_angle(wenc)
    x_cor = radius * math.cos(theta)
    y_cor = radius * math.sin(theta)
    # get xy
    x, y = trans_xy_r2w(x_cor, y_cor, notch_theta=0.0, x_shift=0.0, y_shift=0.0)
    return x, y