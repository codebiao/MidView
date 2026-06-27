"""Coordinate conversion utilities for wafer visualization."""

import math

from frontend import global_param as _cfg
from frontend.coordinate_correction import correct_coordinate


def xenc_to_radius(xenc: float) -> float:
    radius = _cfg.my_param.scan_start_radius - (xenc - _cfg.my_param.xenc_start) * _cfg.xenc_resolution
    return radius if radius > 0.0 else 10.0


def wenc_to_angle(wenc: float) -> float:
    theta = -((wenc / _cfg.WENC_MAX) * 2.0 * math.pi)
    return theta


def xwenc_to_xy(xenc: float, wenc: float) -> tuple[float, float]:
    radius = xenc_to_radius(xenc)
    theta = wenc_to_angle(wenc)
    x_cor = radius * math.cos(theta)
    y_cor = radius * math.sin(theta)

    x,y=correct_coordinate(_cfg.my_param.xycal_param, _cfg.my_param.eds_param, x_cor, y_cor)
    return x, y