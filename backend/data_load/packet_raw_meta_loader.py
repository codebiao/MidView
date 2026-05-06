"""Load packet metadata from packet_raw_meta.csv and binary image data."""

from __future__ import annotations

import csv
import os
from backend.models import PacketRawMeta
from backend.data_load._helpers import safe_int, safe_float


def load_packet_raw_meta(folder_path: str) -> list[PacketRawMeta]:
    filepath = os.path.join(folder_path, "packet_raw_meta.csv")
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"packet_raw_meta.csv not found in {folder_path}")

    packet_raw_meta_array: list[PacketRawMeta] = []

    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row_num, row in enumerate(reader, start=2):
            try:
                p = PacketRawMeta(
                    packet_id=safe_int(row["packet_id"]),
                    from_proc_id=safe_int(row["from_proc_id"]),
                    track_id_start=safe_int(row["track_id_start"]),
                    track_id_end=safe_int(row["track_id_end"]),
                    addr=safe_int(row["addr"]),
                    size=safe_int(row["size"]),
                    xenc_outer=safe_float(row["xenc_outer"]),
                    xenc_inner=safe_float(row["xenc_inner"]),
                    wenc_left=safe_float(row["wenc_left"]),
                    wenc_right=safe_float(row["wenc_right"]),
                )
                packet_raw_meta_array.append(p)
            except Exception as e:
                raise type(e)(
                    f"{filepath} line {row_num}: {e}"
                ) from e

    return packet_raw_meta_array


def find_packet_meta(
    packet_id: int, packet_raw_meta_array: list[PacketRawMeta]
) -> PacketRawMeta | None:
    for p in packet_raw_meta_array:
        if p.packet_id == packet_id:
            return p
    return None
