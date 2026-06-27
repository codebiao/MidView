from dataclasses import dataclass, field


@dataclass
class PacketMeta:
    pkg_index: int
    packet_id: int
    from_proc_id: int
    is_center: int = 0
    pkg_row_start: int = 0
    pkg_row_end: int = 0
    pkg_col_start: int = 0
    pkg_col_end: int = 0
    img_row_start: int = 0
    img_col_start: int = 0
    img_row_count: int = 0
    img_col_count: int = 0


@dataclass
class ImageMeta:
    img_id: int = -1
    is_valid: int = 0
    scale: float = 1.0
    proc_id: int = -1
    file_name: str = ""
    pos: int = 0
    angle_deg: float = 0.0
    overlap_pixels_prev: int = 0
    overlap_pixels_next: int = 0
    tag: int = 0
    packet_array: list[PacketMeta] = field(default_factory=list)
    packet_array_count: int = 0
