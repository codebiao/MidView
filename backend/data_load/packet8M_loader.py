"""Parse 8MB binary packet image files."""

import struct
from dataclasses import dataclass
import numpy as np

FILE_SIZE = 8388608  # 8MB
HEADER_BYTES = 64
FOOTER_BYTES = 8
ENCODER_BYTES = 8
LINEINFO_BYTES = 96  # optional, only present if line_info_enable == 1
@dataclass
class Header:
    packet_id: int
    version: int
    nimc_num: int
    sensor_mono: int
    sensor_width: int
    sensor_height: int
    line_info_enable: int
    reserve1: int
    reserve2: bytes


@dataclass
class Footer:
    check_sum: int
    valid_line: int
    cr_flag: int
    packet_end: int

@dataclass
class Encoder:
    wenc: int
    ttl_linerate_cyc: int
    reserve: int
    xenc: int
    unwrapping_number: int
    reserve2: int
    cr: int
    acc: int
    trig: int


@dataclass
class Packet8M:
    head: Header
    data: np.ndarray
    lineinfo: np.ndarray | None
    encoder: list[Encoder]
    footer: Footer


def load_packet8M(file_path: str) -> Packet8M:
    """Parse a fixed 8MB binary packet image file. Returns a Packet8M."""
    with open(file_path, "rb") as f:
        content = f.read()

    if len(content) != FILE_SIZE:
        raise ValueError(
            f"File size mismatch: got {len(content)} bytes, "
            f"expected {FILE_SIZE} bytes."
        )

    # 1. Header (64 bytes)
    hu = struct.unpack("<8I32s", content[:64])  # 小端序：8 个 uint32 + 32 字节字符数组 = 64 字节
    head = Header(
        packet_id = hu[0],
        version = hu[1],
        nimc_num = hu[2],
        sensor_mono = hu[3],
        sensor_width = hu[4],
        sensor_height = hu[5],
        line_info_enable = hu[6],
        reserve1=hu[7],
        reserve2=hu[8],
    )

    # 2. Footer (8 bytes)
    fv = struct.unpack("<Q", content[-8:])[0]   # 小端序：1 个 uint64 = 8 字节
    footer = Footer(
        check_sum=fv & 0xFFFFFF,                  # bits  0..23  (24 bits)
        valid_line=(fv >> 24) & 0x7FFFFF,         # bits 24..46  (23 bits)
        cr_flag=(fv >> 47) & 0x1,                 # bit  47      (1 bit)
        packet_end=(fv >> 48) & 0xFFFF,           # bits 48..63  (16 bits, sentinel 0xABAB)
    )

    # 3. Data + Encoder (+ optional LineInfo)
    sensor_width = head.sensor_width
    valid_line = footer.valid_line
    has_lineinfo = head.line_info_enable == 1
    extra_bytes = LINEINFO_BYTES if has_lineinfo else 0
    line_bytes = sensor_width * 2 + 8 + extra_bytes
    data_offset = HEADER_BYTES
    valid_data_length = valid_line * line_bytes

    raw_valid_data = content[data_offset : data_offset + valid_data_length]
    raw_array = np.frombuffer(
        raw_valid_data, dtype=np.uint8
    ).reshape(valid_line, line_bytes)

    image_bytes = np.ascontiguousarray(raw_array[:, : sensor_width * 2])
    data = image_bytes.view(dtype="<u2") 

    encoder_raw_bytes = np.ascontiguousarray(
        raw_array[:, sensor_width * 2 : sensor_width * 2 + 8]
    )
    ev = encoder_raw_bytes.view(dtype="<Q").flatten()   # 小端序：8 个 uint64 = 64 字节

    encoder = [
        Encoder(
            wenc=int(v & 0x3FFFF),                    # bits  0..17  (18 bits)
            ttl_linerate_cyc=int((v >> 18) & 0xFFF),  # bits 18..29  (12 bits)
            reserve=int((v >> 30) & 0x3),              # bits 30..31  (2 bits)
            xenc=int((v >> 32) & 0x3FFFF),             # bits 32..49  (18 bits)
            unwrapping_number=int((v >> 50) & 0xFF),   # bits 50..57  (8 bits)
            reserve2=int((v >> 58) & 0x7),             # bits 58..60  (3 bits)
            cr=int((v >> 61) & 0x1),                   # bit  61      (1 bit)
            acc=int((v >> 62) & 0x1),                  # bit  62      (1 bit)
            trig=int((v >> 63) & 0x1),                 # bit  63      (1 bit)
        )
        for v in ev
    ]

    if has_lineinfo:
        lineinfo = np.ascontiguousarray(
            raw_array[:, sensor_width * 2 + 8 :].copy()
        )
    else:
        lineinfo = None

    return Packet8M(
        head=head,
        data=data,
        lineinfo=lineinfo,
        encoder=encoder,
        footer=footer,
    )
