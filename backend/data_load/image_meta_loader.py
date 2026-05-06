"""Load image metadata from img_and_packet_meta.csv.

CSV format (31 columns per row):
  Header row:  ImageMeta fields in cols 0-11, "-" in PacketMeta cols 15-30
  Packet row:  "-" in cols 0-14, BucketNode in cols 15-18, PacketMeta in cols 19-30
"""

from __future__ import annotations

import csv
import os
from backend.models import ImageMeta, PacketMeta
from backend.data_load._helpers import safe_int, safe_float


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
    try:
        safe_int(rows[0][0])
    except ValueError:
        start = 1

    i = start
    img_count = 0
    while i < len(rows):
        row = rows[i]
        if len(row) < 31:
            i += 1
            continue

        line_num = i + start + 1  # 1-based, account for header skip
        try:
            # header row: ImageMeta from cols 0-11
            img_id = safe_int(row[1], -1)
            is_valid = safe_int(row[2], 0)
            scale = safe_float(row[3], 1.0)
            proc_id = safe_int(row[4], -1)
            file_name = row[5]
            pos = safe_int(row[6], 0)
            angle_deg = safe_float(row[7], 0.0)
            overlap_pixels_prev = safe_int(row[8], 0)
            overlap_pixels_next = safe_int(row[9], 0)
            packet_array_count = safe_int(row[10], 0)
            tag = safe_int(row[11], 0)

            packet_array: list[PacketMeta] = []
            for _ in range(packet_array_count):
                i += 1
                if i >= len(rows):
                    break
                pkt_row = rows[i]
                if len(pkt_row) < 31:
                    break
                pkt_line = i + start + 1
                try:
                    pkt = PacketMeta(
                        pkg_index=safe_int(pkt_row[19], 0),
                        packet_id=safe_int(pkt_row[20], 0),
                        from_proc_id=safe_int(pkt_row[21], 0),
                        is_center=safe_int(pkt_row[22], 0),
                        pkg_row_start=safe_int(pkt_row[23], 0),
                        pkg_row_end=safe_int(pkt_row[24], 0),
                        pkg_col_start=safe_int(pkt_row[25], 0),
                        pkg_col_end=safe_int(pkt_row[26], 0),
                        img_row_start=safe_int(pkt_row[27], 0),
                        img_col_start=safe_int(pkt_row[28], 0),
                        img_row_count=safe_int(pkt_row[29], 0),
                        img_col_count=safe_int(pkt_row[30], 0),
                    )
                    packet_array.append(pkt)
                except Exception as e:
                    raise type(e)(
                        f"{filepath} line {pkt_line}: {e}"
                    ) from e

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
            img_count += 1
        except Exception as e:
            raise type(e)(
                f"{filepath} line {line_num}: {e}"
            ) from e

        i += 1

    return result
