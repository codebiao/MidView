from dataclasses import dataclass


@dataclass
class PacketRawMeta:
    packet_id: int
    from_proc_id: int
    track_id_start: int
    track_id_end: int
    addr: int
    size: int
    xenc_outer: float
    xenc_inner: float
    wenc_left: float
    wenc_right: float
