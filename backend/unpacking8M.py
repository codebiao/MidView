"""Parser for fixed 8MB binary image files."""

from __future__ import annotations

import struct
import numpy as np


def parser_8M(file_path: str) -> tuple[dict, np.ndarray, dict]:
    file_size = 8388608

    with open(file_path, "rb") as f:
        content = f.read()

    if len(content) != file_size:
        raise ValueError(
            f"File size mismatch: got {len(content)} bytes, expected {file_size}"
        )

    head_data = content[:64]
    head_unpacked = struct.unpack("<6I40s", head_data)

    head = {
        "packet_id": head_unpacked[0],
        "version": head_unpacked[1],
        "nimc_num": head_unpacked[2],
        "sensor_mono": head_unpacked[3],
        "sensor_width": head_unpacked[4],
        "sensor_height": head_unpacked[5],
        "reserve2": head_unpacked[6],
    }

    footer_data = content[-8:]
    footer_val = struct.unpack("<Q", footer_data)[0]

    footer = {
        "check_sum": footer_val & 0xFFFFFF,
        "valid_line": (footer_val >> 24) & 0x7FFFFF,
        "cr_flag": (footer_val >> 47) & 0x1,
        "packet_end": (footer_val >> 48) & 0xFFFF,
    }

    sensor_width = head["sensor_width"]
    valid_line = footer["valid_line"]

    line_bytes = sensor_width * 2 + 8
    data_offset = 64
    valid_data_length = valid_line * line_bytes

    raw_valid_data = content[data_offset : data_offset + valid_data_length]
    raw_array = np.frombuffer(raw_valid_data, dtype=np.uint8).reshape(
        valid_line, line_bytes
    )

    image_bytes = raw_array[:, : sensor_width * 2]
    image_bytes_contiguous = np.ascontiguousarray(image_bytes)
    data = image_bytes_contiguous.view(dtype="<u2")

    return head, data, footer
