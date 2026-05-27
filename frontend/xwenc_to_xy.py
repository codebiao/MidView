"""Coordinate conversion utilities for wafer visualization."""

import math

from frontend import global_param as _cfg


def xenc_to_radius(xenc: float) -> float:
    radius = _cfg.scan_start_radius - (xenc - _cfg.xenc_start) * _cfg.xenc_resolution
    return radius if radius > 0.0 else 10.0


def wenc_to_angle(wenc: float) -> float:
    theta = -((wenc / _cfg.WENC_MAX) * 2.0 * math.pi)
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
    x, y = trans_xy_r2w(x_cor, y_cor, notch_theta=_cfg.notch_theta, x_shift=_cfg.x_shift, y_shift=_cfg.y_shift)
    return x, y