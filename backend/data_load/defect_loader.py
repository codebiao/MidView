"""Load defect data from defects.csv."""

from __future__ import annotations

import csv
import os
from backend.models import Defect


def load_defects(folder_path: str) -> list[Defect]:
    filepath = os.path.join(folder_path, "defects.csv")
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"defects.csv not found in {folder_path}")

    defect_array: list[Defect] = []

    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            d = Defect(
                index=int(row["index"]),
                parent=int(row["parent"]),
                next=int(row["next"]),
                tail=int(row["tail"]),
                count=int(row["count"]),
                status=int(row["status"]),
                track_id=int(row["track_id"]),
                source_type=int(row["source_type"]),
                defect_id=int(row["dft.defect_id"]),
                event_root_index=int(row["dft.event_root_index"]),
                from_channel=int(row["dft.from_channel"]),
                channel_defect_id=int(row["dft.channel_defect_id"]),
                related_defect_id=int(row["dft.related_defect_id"]),
                img_id=int(row["dft.img_id"]),
                img_tag=int(row["dft.img_tag"]),
                peak_adc=float(row["dft.peak_adc"]),
                peak_packet_id=int(row["dft.peak_packet_id"]),
                peak_row=float(row["dft.peak_row"]),
                peak_col=float(row["dft.peak_col"]),
                x_encoder=float(row["dft.x_encoder"]),
                w_encoder=float(row["dft.w_encoder"]),
                radius=float(row["dft.radius"]),
                theta=float(row["dft.theta"]),
                x_cor=float(row["dft.x_cor"]),
                y_cor=float(row["dft.y_cor"]),
                x=float(row["dft.x"]),
                y=float(row["dft.y"]),
                snr=float(row["dft.snr"]),
                defect_area=float(row["dft.defect_area"]),
                defect_size=float(row["dft.defect_size"]),
                dsize=float(row["dft.dsize"]),
                rppm=float(row["dft.rppm"]),
                nppm=float(row["dft.nppm"]),
                um_size=float(row["dft.um_size"]),
                x_size=float(row["dft.x_size"]),
                y_size=float(row["dft.y_size"]),
                ee=float(row["dft.ee"]),
                haze_avg=float(row["dft.haze_avg"]),
                defect_tag=int(row["dft.defect_tag"]),
                cluster_number=int(row["dft.cluster_number"]),
                cluster_area=float(row["dft.cluster_area"]),
                cluster_length=float(row["dft.cluster_length"]),
                confidence=float(row["dft.confidence"]),
                midlevel_bin_number=int(row["dft.midlevel_bin_number"]),
                rough_bin_number=int(row["dft.rough_bin_number"]),
                fine_bin_number=int(row["dft.fine_bin_number"]),
                acc_flag=int(row["dft.acc_flag"]),
                cosmic_ray_flag=int(row["dft.cosmic_ray_flag"]),
                saturated_flag=int(row["dft.saturated_flag"]),
                max_xt_fit=float(row["dft.max_xt_fit"]),
                xenc_outer=float(row["dft.xenc_outer"]),
                xenc_inner=float(row["dft.xenc_inner"]),
                wenc_left=float(row["dft.wenc_left"]),
                wenc_right=float(row["dft.wenc_right"]),
            )
            defect_array.append(d)

    return defect_array
