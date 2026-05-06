"""Load image metadata from img_and_packet_meta.csv.

CSV format (31 columns per row):
  Header row:  ImageMeta fields in cols 0-11, "-" in PacketMeta cols 15-30
  Packet row:  "-" in cols 0-14, BucketNode in cols 15-18, PacketMeta in cols 19-30
"""

from __future__ import annotations

import csv
import os
from backend.models import ImageMeta, PacketMeta


def _parse_int(s: str) -> int | None:
    try:
        return int(s)
    except (ValueError, TypeError):
        return None


def _parse_float(s: str) -> float | None:
    try:
        return float(s)
    except (ValueError, TypeError):
        return None


def load_image_meta(folder_path: str) -> list[ImageMeta]:
    filepath = os.path.join(folder_path, "img_and_packet_meta.csv")
    if not os.path.exists(filepath):
        raise FileNotFoundError(
            f"img_and_packet_meta.csv not found in {folder_path}"
        )

    result: list[ImageMeta] = []

    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)

    if not rows:
        return result

    # skip column header row
    start = 0
    if _parse_int(rows[0][0]) is None:
        start = 1

    i = start
    while i < len(rows):
        row = rows[i]
        if len(row) < 31:
            i += 1
            continue

        # header row: ImageMeta from cols 0-11
        img_id = _parse_int(row[1]) or -1
        is_valid = _parse_int(row[2]) or 0
        scale = _parse_float(row[3]) or 1.0
        proc_id = _parse_int(row[4]) or -1
        file_name = row[5]
        pos = _parse_int(row[6]) or 0
        angle_deg = _parse_float(row[7]) or 0.0
        overlap_pixels_prev = _parse_int(row[8]) or 0
        overlap_pixels_next = _parse_int(row[9]) or 0
        packet_array_count = _parse_int(row[10]) or 0
        tag = _parse_int(row[11]) or 0

        packet_array: list[PacketMeta] = []
        for _ in range(packet_array_count):
            i += 1
            if i >= len(rows):
                break
            pkt_row = rows[i]
            if len(pkt_row) < 31:
                break
            pkt = PacketMeta(
                pkg_index=_parse_int(pkt_row[19]) or 0,
                packet_id=_parse_int(pkt_row[20]) or 0,
                from_proc_id=_parse_int(pkt_row[21]) or 0,
                is_center=_parse_int(pkt_row[22]) or 0,
                pkg_row_start=_parse_int(pkt_row[23]) or 0,
                pkg_row_end=_parse_int(pkt_row[24]) or 0,
                pkg_col_start=_parse_int(pkt_row[25]) or 0,
                pkg_col_end=_parse_int(pkt_row[26]) or 0,
                img_row_start=_parse_int(pkt_row[27]) or 0,
                img_col_start=_parse_int(pkt_row[28]) or 0,
                img_row_count=_parse_int(pkt_row[29]) or 0,
                img_col_count=_parse_int(pkt_row[30]) or 0,
            )
            packet_array.append(pkt)

        result.append(
            ImageMeta(
                img_id=img_id,
                is_valid=is_valid,
                scale=scale,
                proc_id=proc_id,
                file_name=file_name,
                pos=pos,
                angle_deg=angle_deg,
                overlap_pixels_prev=overlap_pixels_prev,
                overlap_pixels_next=overlap_pixels_next,
                tag=tag,
                packet_array=packet_array,
                packet_array_count=packet_array_count,
            )
        )

        i += 1

    return result
