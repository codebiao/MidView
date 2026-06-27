"""Load defect data from defects.csv."""

from __future__ import annotations

import csv
import os
from backend.models import Defect
from backend.data_load._helpers import safe_int, safe_float


def load_defects(folder_path: str) -> list[Defect]:
    filepath = os.path.join(folder_path, "defects.csv")
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"defects.csv not found in {folder_path}")

    defect_array: list[Defect] = []

    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row_num, row in enumerate(reader, start=2):
            try:
                d = Defect(
                    index=safe_int(row["index"]),
                    parent=safe_int(row["parent"]),
                    next=safe_int(row["next"]),
                    tail=safe_int(row["tail"]),
                    count=safe_int(row["count"]),
                    status=safe_int(row["status"]),
                    track_id=safe_int(row["track_id"]),
                    source_type=safe_int(row["source_type"]),
                    defect_id=safe_int(row["dft.defect_id"]),
                    event_root_index=safe_int(row["dft.event_root_index"]),
                    from_channel=safe_int(row["dft.from_channel"]),
                    channel_defect_id=safe_int(row["dft.channel_defect_id"]),
                    related_defect_id=safe_int(row["dft.related_defect_id"]),
                    img_id=safe_int(row["dft.img_id"]),
                    img_tag=safe_int(row["dft.img_tag"]),
                    peak_adc=safe_float(row["dft.peak_adc"]),
                    peak_packet_id=safe_int(row["dft.peak_packet_id"]),
                    peak_row=safe_float(row["dft.peak_row"]),
                    peak_col=safe_float(row["dft.peak_col"]),
                    x_encoder=safe_float(row["dft.x_encoder"]),
                    w_encoder=safe_float(row["dft.w_encoder"]),
                    radius=safe_float(row["dft.radius"]),
                    theta=safe_float(row["dft.theta"]),
                    x_cor=safe_float(row["dft.x_cor"]),
                    y_cor=safe_float(row["dft.y_cor"]),
                    x=safe_float(row["dft.x"]),
                    y=safe_float(row["dft.y"]),
                    snr=safe_float(row["dft.snr"]),
                    defect_area=safe_float(row["dft.defect_area"]),
                    defect_size=safe_float(row["dft.defect_size"]),
                    dsize=safe_float(row["dft.dsize"]),
                    rppm=safe_float(row["dft.rppm"]),
                    nppm=safe_float(row["dft.nppm"]),
                    um_size=safe_float(row["dft.um_size"]),
                    x_size=safe_float(row["dft.x_size"]),
                    y_size=safe_float(row["dft.y_size"]),
                    ee=safe_float(row["dft.ee"]),
                    haze_avg=safe_float(row["dft.haze_avg"]),
                    defect_tag=safe_int(row["dft.defect_tag"]),
                    cluster_number=safe_int(row["dft.cluster_number"]),
                    cluster_area=safe_float(row["dft.cluster_area"]),
                    cluster_length=safe_float(row["dft.cluster_length"]),
                    confidence=safe_float(row["dft.confidence"]),
                    midlevel_bin_number=safe_int(row["dft.midlevel_bin_number"]),
                    rough_bin_number=safe_int(row["dft.rough_bin_number"]),
                    fine_bin_number=safe_int(row["dft.fine_bin_number"]),
                    acc_flag=safe_int(row["dft.acc_flag"]),
                    cosmic_ray_flag=safe_int(row["dft.cosmic_ray_flag"]),
                    saturated_flag=safe_int(row["dft.saturated_flag"]),
                    max_xt_fit=safe_float(row["dft.max_xt_fit"]),
                    xenc_outer=safe_float(row["dft.xenc_outer"]),
                    xenc_inner=safe_float(row["dft.xenc_inner"]),
                    wenc_left=safe_float(row["dft.wenc_left"]),
                    wenc_right=safe_float(row["dft.wenc_right"]),
                    from_proc_id=safe_int(row.get("dft.from_proc_id", "0")),
                    proc_id=safe_int(row.get("dft.proc_id", "0")),
                    signal_type=safe_int(row.get("dft.signal_type", "0")),
                    r_size=safe_float(row.get("dft.r_size", "0")),
                    t_size=safe_float(row.get("dft.t_size", "0")),
                    median_r_size=safe_float(row.get("dft.median_r_size", "0")),
                    median_t_size=safe_float(row.get("dft.median_t_size", "0")),
                    r_cluster_size=safe_float(row.get("dft.r_cluster_size", "0")),
                    t_cluster_size=safe_float(row.get("dft.t_cluster_size", "0")),
                )
                defect_array.append(d)
            except Exception as e:
                raise type(e)(
                    f"{filepath} line {row_num}: {e}"
                ) from e

    return defect_array
