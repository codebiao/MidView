"""Load packet metadata from packet_raw_meta.csv and binary image data."""

from __future__ import annotations

import csv
import os
from backend.models import PacketRawMeta


def load_packet_raw_meta(folder_path: str) -> list[PacketRawMeta]:
    filepath = os.path.join(folder_path, "packet_raw_meta.csv")
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"packet_raw_meta.csv not found in {folder_path}")

    packet_raw_meta_array: list[PacketRawMeta] = []

    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            p = PacketRawMeta(
                packet_id=int(row["packet_id"]),
                from_proc_id=int(row["from_proc_id"]),
                track_id_start=int(row["track_id_start"]),
                track_id_end=int(row["track_id_end"]),
                addr=int(row["addr"]),
                size=int(row["size"]),
                xenc_outer=float(row["xenc_outer"]),
                xenc_inner=float(row["xenc_inner"]),
                wenc_left=float(row["wenc_left"]),
                wenc_right=float(row["wenc_right"]),
            )
            packet_raw_meta_array.append(p)

    return packet_raw_meta_array


def find_packet_meta(
    packet_id: int, packet_raw_meta_array: list[PacketRawMeta]
) -> PacketRawMeta | None:
    for p in packet_raw_meta_array:
        if p.packet_id == packet_id:
            return p
    return None
