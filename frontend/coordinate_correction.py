"""Coordinate correction — Python port of ZPXYCAL::CoordinateCorrection."""

from __future__ import annotations

import math

from backend.models.my_param import XyCalParam, EdsParam

PI_2 = math.pi / 2.0
_EPSILON = 1e-12


def correct_rotation(theta: float, x_in: float, y_in: float) -> tuple[float, float]:
    """2D rotation by theta radians."""
    s = math.sin(theta)
    c = math.cos(theta)
    return (x_in * c - y_in * s, x_in * s + y_in * c)


def correct_r_scale(r_scale: float, x_in: float, y_in: float) -> tuple[float, float]:
    return (x_in * r_scale, y_in * r_scale)


def correct_delta_xyl(delta_xl: float, delta_yl: float,
                      x_in: float, y_in: float) -> tuple[float, float]:
    r2 = x_in * x_in + y_in * y_in
    if r2 < _EPSILON:
        return (x_in, y_in)

    delta_yl_sq = delta_yl * delta_yl
    if r2 <= delta_yl_sq:
        return (x_in, y_in)

    lf_corr_r_delta = math.sqrt(r2 - delta_yl_sq)
    lf_corr_r = lf_corr_r_delta + delta_xl
    denom = delta_yl_sq + lf_corr_r_delta * lf_corr_r_delta
    if denom < _EPSILON:
        return (x_in, y_in)

    sin_t = (y_in * lf_corr_r_delta - x_in * delta_yl) / denom
    cos_t = (x_in + delta_yl * sin_t) / lf_corr_r_delta
    return (lf_corr_r * cos_t, lf_corr_r * sin_t)


def correct_xy_shift(x_shift: float, y_shift: float,
                     x_in: float, y_in: float) -> tuple[float, float]:
    return (x_in + x_shift, y_in + y_shift)


def correct_xycali_without_shift(xycal_param: XyCalParam, x_in: float, y_in: float) -> tuple[float, float]:
    x, y = correct_rotation(xycal_param.rotation, x_in, y_in)
    x, y = correct_r_scale(xycal_param.r_scale, x, y)
    x, y = correct_delta_xyl(xycal_param.delta_xl, xycal_param.delta_yl, x, y)
    return (x, y)


def correct_xycali(xycal_param: XyCalParam, x_in: float, y_in: float) -> tuple[float, float]:
    x, y = correct_xycali_without_shift(xycal_param, x_in, y_in)
    x, y = correct_xy_shift(xycal_param.x_shift, xycal_param.y_shift, x, y)
    return (x, y)


def correct_eds_r2w(eds_param: EdsParam, x_in: float, y_in: float) -> tuple[float, float]:
    notch_theta = eds_param.notch_theta - PI_2
    x, y = correct_rotation(notch_theta, x_in, y_in)
    x += eds_param.x_shift
    y += eds_param.y_shift
    x, y = correct_rotation(-eds_param.epsilon, x, y)
    return (x, y)


def correct_eds_w2r(eds_param: EdsParam, x_in: float, y_in: float) -> tuple[float, float]:
    x, y = correct_rotation(eds_param.epsilon, x_in, y_in)
    x -= eds_param.x_shift
    y -= eds_param.y_shift
    notch_theta = -(eds_param.notch_theta - PI_2)
    x, y = correct_rotation(notch_theta, x, y)
    return (x, y)


def correct_coordinate(xycal_param: XyCalParam, eds_param: EdsParam,
                       x_in: float, y_in: float) -> tuple[float, float]:
    x, y = correct_xycali_without_shift(xycal_param, x_in, y_in)
    x, y = correct_eds_r2w(eds_param, x, y)
    return (x, y)
