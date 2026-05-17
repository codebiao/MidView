"""Load event data from events.csv.

Pointer fields (this_ptr, parent, next, prev, next_track, prev_track, track_root)
are stored as indices into the event_array.
"""

from __future__ import annotations

import csv
import os
from backend.models import Event
from backend.data_load._helpers import safe_int, safe_float


def load_events(folder_path: str) -> list[Event]:
    filepath = os.path.join(folder_path, "events.csv")
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"events.csv not found in {folder_path}")

    event_array: list[Event] = []

    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row_num, row in enumerate(reader, start=2):
            try:
                evt = Event(
                    index=len(event_array),
                    this_ptr=safe_int(row["this_ptr"]),
                    parent=safe_int(row["parent"]),
                    next=safe_int(row["next"]),
                    prev=safe_int(row["prev"]),
                    next_track=safe_int(row["next_track"]),
                    prev_track=safe_int(row["prev_track"]),
                    track_root=safe_int(row["track_root"]),
                    count=safe_int(row["count"]),
                    track_count=safe_int(row["track_count"]),
                    track_node_count=safe_int(row["track_node_count"]),
                    status=safe_int(row["status"]),
                    track_id=safe_int(row["track_id"]),
                    event_id=safe_int(row["evt.event_id"]),
                    defect_id=safe_int(row["evt.defect_id"]),
                    proc_id=safe_int(row["evt.proc_id"]),
                    packet_id=safe_int(row["evt.packet_id"]),
                    peak_adc=safe_float(row["evt.peak_adc"]),
                    peak_row=safe_float(row["evt.peak_row"]),
                    peak_col=safe_float(row["evt.peak_col"]),
                    x_encoder=safe_float(row["evt.x_encoder"]),
                    w_encoder=safe_float(row["evt.w_encoder"]),
                    radius=safe_float(row["evt.radius"]),
                    theta=safe_float(row["evt.theta"]),
                    x_cor=safe_float(row["evt.x_cor"]),
                    y_cor=safe_float(row["evt.y_cor"]),
                    x=safe_float(row["evt.x"]),
                    y=safe_float(row["evt.y"]),
                    snr=safe_float(row["evt.snr"]),
                    ee=safe_float(row["evt.ee"]),
                    ee_is_fitted=safe_int(row["evt.ee_is_fitted"]),
                    xenc_merge_count=safe_float(row["evt.xenc_merge_count"]),
                    wenc_merge_count=safe_float(row["evt.wenc_merge_count"]),
                    wenc_per_um=safe_float(row["evt.wenc_per_um"]),
                    check_sum=safe_int(row["evt.check_sum"]),
                    box_x=safe_float(row["evt.box_x"]),
                    box_y=safe_float(row["evt.box_y"]),
                    box_width=safe_float(row["evt.box_width"]),
                    box_height=safe_float(row["evt.box_height"]),
                    compressed2_box_x=safe_float(row["evt.compressed2_box_x"]),
                    compressed2_box_y=safe_float(row["evt.compressed2_box_y"]),
                    compressed2_box_width=safe_float(row["evt.compressed2_box_width"]),
                    compressed2_box_height=safe_float(row["evt.compressed2_box_height"]),
                    xenc_outer=safe_float(row["evt.xenc_outer"]),
                    xenc_inner=safe_float(row["evt.xenc_inner"]),
                    wenc_left=safe_float(row["evt.wenc_left"]),
                    wenc_right=safe_float(row["evt.wenc_right"]),
                    acc_flag=safe_int(row["evt.acc_flag"]),
                    cosmic_ray_flag=safe_int(row["evt.cosmic_ray_flag"]),
                    saturated_flag=safe_int(row["evt.saturated_flag"]),
                    pixel_sindex=safe_int(row["evt.pixel_sindex"]),
                    pixel_eindex=safe_int(row["evt.pixel_eindex"]),
                )
                event_array.append(evt)
            except Exception as e:
                raise type(e)(
                    f"{filepath} line {row_num}: {e}"
                ) from e

    return event_array


def get_event_chain(root_index: int, event_array: list[Event]) -> list[Event]:
    """Traverse the event linked list starting from root_index via 'next' pointers."""
    chain: list[Event] = []
    if root_index < 0 or root_index >= len(event_array):
        return chain

    visited: set[int] = set()
    idx = root_index
    while idx >= 0 and idx < len(event_array) and idx not in visited:
        visited.add(idx)
        chain.append(event_array[idx])
        idx = event_array[idx].next

    return chain
