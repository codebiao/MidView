"""Load event data from events.csv.

Pointer fields (this_ptr, parent, next, prev, next_track, prev_track, track_root)
are stored as indices into the event_array.
"""

from __future__ import annotations

import csv
import os
from backend.models import Event


def load_events(folder_path: str) -> list[Event]:
    filepath = os.path.join(folder_path, "events.csv")
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"events.csv not found in {folder_path}")

    event_array: list[Event] = []

    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            evt = Event(
                index=len(event_array),
                this_ptr=int(row["this_ptr"]),
                parent=int(row["parent"]),
                next=int(row["next"]),
                prev=int(row["prev"]),
                next_track=int(row["next_track"]),
                prev_track=int(row["prev_track"]),
                track_root=int(row["track_root"]),
                count=int(row["count"]),
                track_count=int(row["track_count"]),
                track_node_count=int(row["track_node_count"]),
                status=int(row["status"]),
                track_id=int(row["track_id"]),
                event_id=int(row["evt.event_id"]),
                proc_id=int(row["evt.proc_id"]),
                packet_id=int(row["evt.packet_id"]),
                peak_adc=float(row["evt.peak_adc"]),
                peak_row=float(row["evt.peak_row"]),
                peak_col=float(row["evt.peak_col"]),
                x_encoder=float(row["evt.x_encoder"]),
                w_encoder=float(row["evt.w_encoder"]),
                radius=float(row["evt.radius"]),
                theta=float(row["evt.theta"]),
                x_cor=float(row["evt.x_cor"]),
                y_cor=float(row["evt.y_cor"]),
                x=float(row["evt.x"]),
                y=float(row["evt.y"]),
                snr=float(row["evt.snr"]),
                ee=float(row["evt.ee"]),
                ee_is_fitted=int(row["evt.ee_is_fitted"]),
                xenc_merge_count=float(row["evt.xenc_merge_count"]),
                wenc_merge_count=float(row["evt.wenc_merge_count"]),
                wenc_per_um=float(row["evt.wenc_per_um"]),
                box_width=float(row["evt.box_width"]),
                box_height=float(row["evt.box_height"]),
                xenc_outer=float(row["evt.xenc_outer"]),
                xenc_inner=float(row["evt.xenc_inner"]),
                wenc_left=float(row["evt.wenc_left"]),
                wenc_right=float(row["evt.wenc_right"]),
                acc_flag=int(row["evt.acc_flag"]),
                cosmic_ray_flag=int(row["evt.cosmic_ray_flag"]),
                saturated_flag=int(row["evt.saturated_flag"]),
                pixel_sindex=int(row["evt.pixel_sindex"]),
                pixel_eindex=int(row["evt.pixel_eindex"]),
            )
            event_array.append(evt)

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
