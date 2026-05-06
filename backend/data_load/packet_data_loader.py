"""Parse 8MB binary packet image files."""

import struct
import numpy as np


def load_packet_data(file_path: str):
    """Parse a fixed 8MB binary image file.

    Returns (head, data, encoder, footer) where:
      - head: dict with packet_id, version, nimc_num, sensor_mono, sensor_width,
              sensor_height
      - data: 2D uint16 numpy array of pixel values
      - encoder: dict with wenc, ttl_linerate_cyc, xenc, unwrapping_number, etc.
      - footer: dict with check_sum, valid_line, cr_flag, packet_end
    """
    FILE_SIZE = 8388608  # 8MB

    with open(file_path, "rb") as f:
        content = f.read()

    if len(content) != FILE_SIZE:
        raise ValueError(
            f"File size mismatch: got {len(content)} bytes, "
            f"expected {FILE_SIZE} bytes."
        )

    # 1. Head (64 bytes)
    head_unpacked = struct.unpack("<6I40s", content[:64])
    head = {
        "packet_id": head_unpacked[0],
        "version": head_unpacked[1],
        "nimc_num": head_unpacked[2],
        "sensor_mono": head_unpacked[3],
        "sensor_width": head_unpacked[4],
        "sensor_height": head_unpacked[5],
        "reserve2": head_unpacked[6],
    }

    # 2. Footer (8 bytes)
    footer_val = struct.unpack("<Q", content[-8:])[0]
    footer = {
        "check_sum": footer_val & 0xFFFFFF,
        "valid_line": (footer_val >> 24) & 0x7FFFFF,
        "cr_flag": (footer_val >> 47) & 0x1,
        "packet_end": (footer_val >> 48) & 0xFFFF,
    }

    # 3. Data + Encoder
    sensor_width = head["sensor_width"]
    valid_line = footer["valid_line"]
    line_bytes = sensor_width * 2 + 8
    data_offset = 64
    valid_data_length = valid_line * line_bytes

    raw_valid_data = content[data_offset : data_offset + valid_data_length]
    raw_array = np.frombuffer(
        raw_valid_data, dtype=np.uint8
    ).reshape(valid_line, line_bytes)

    image_bytes = np.ascontiguousarray(raw_array[:, : sensor_width * 2])
    data = image_bytes.view(dtype="<u2")

    encoder_raw_bytes = np.ascontiguousarray(raw_array[:, sensor_width * 2 :])
    encoder_vals = encoder_raw_bytes.view(dtype="<Q").flatten()

    encoder = {
        "wenc": encoder_vals & 0x3FFFF,
        "ttl_linerate_cyc": (encoder_vals >> 18) & 0xFFF,
        "reserve1": (encoder_vals >> 30) & 0x3,
        "xenc": (encoder_vals >> 32) & 0x3FFFF,
        "unwrapping_number": (encoder_vals >> 50) & 0xFF,
        "reserve2": (encoder_vals >> 58) & 0x7,
        "cr": (encoder_vals >> 61) & 0x1,
        "acc": (encoder_vals >> 62) & 0x1,
        "trig": (encoder_vals >> 63) & 0x1,
    }

    return head, data, encoder, footer
