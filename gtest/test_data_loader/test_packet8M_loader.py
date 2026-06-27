"""Test load_packet8M correctness by generating a synthetic 8MB file."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import struct
import tempfile

import numpy as np

from backend.data_load.packet8M_loader import (
    load_packet8M,
    Header, Footer, Encoder, Packet8M,
    FILE_SIZE, HEADER_BYTES, FOOTER_BYTES, ENCODER_BYTES, LINEINFO_BYTES,
)


def _pack_header(h: Header) -> bytes:
    return struct.pack(
        "<8I32s",
        h.packet_id, h.version, h.nimc_num, h.sensor_mono,
        h.sensor_width, h.sensor_height, h.line_info_enable,
        h.reserve1, h.reserve2,
    )


def _pack_footer(f: Footer) -> bytes:
    val = (f.check_sum & 0xFFFFFF) \
        | ((f.valid_line & 0x7FFFFF) << 24) \
        | ((f.cr_flag & 0x1) << 47) \
        | ((f.packet_end & 0xFFFF) << 48)
    return struct.pack("<Q", val)


def _pack_encoder(e: Encoder) -> int:
    return (e.wenc & 0x3FFFF) \
        | ((e.ttl_linerate_cyc & 0xFFF) << 18) \
        | ((e.reserve & 0x3) << 30) \
        | ((e.xenc & 0x3FFFF) << 32) \
        | ((e.unwrapping_number & 0xFF) << 50) \
        | ((e.reserve2 & 0x7) << 58) \
        | ((e.cr & 0x1) << 61) \
        | ((e.acc & 0x1) << 62) \
        | ((e.trig & 0x1) << 63)


def build_test_file(path: str, head: Header, footer: Footer,
                    encoders: list[Encoder], image_data: np.ndarray,
                    lineinfo: np.ndarray | None = None):
    """Write a valid 8MB packet file."""
    extra = LINEINFO_BYTES if head.line_info_enable == 1 else 0
    line_bytes = head.sensor_width * 2 + ENCODER_BYTES + extra
    valid_data_len = footer.valid_line * line_bytes

    with open(path, "wb") as f:
        f.write(_pack_header(head))

        for i in range(footer.valid_line):
            f.write(image_data[i].tobytes())
            f.write(struct.pack("<Q", _pack_encoder(encoders[i])))
            if head.line_info_enable == 1 and lineinfo is not None:
                f.write(lineinfo[i].tobytes())

        # pad to FILE_SIZE - FOOTER_BYTES
        written = HEADER_BYTES + valid_data_len
        remaining = FILE_SIZE - FOOTER_BYTES - written
        if remaining > 0:
            f.write(b"\x00" * remaining)

        f.write(_pack_footer(footer))


# ── helpers ──────────────────────────────────────────────────────────

def _make_header() -> Header:
    return Header(
        packet_id=42, version=1, nimc_num=0,
        sensor_mono=16, sensor_width=10, sensor_height=1,
        line_info_enable=0, reserve1=0, reserve2=b"\x00" * 32,
    )


def _make_footer() -> Footer:
    return Footer(check_sum=0xABCDEF, valid_line=3, cr_flag=0, packet_end=0xABAB)


def _make_encoders() -> list[Encoder]:
    return [
        Encoder(wenc=100, ttl_linerate_cyc=5, reserve=1, xenc=1000,
                unwrapping_number=3, reserve2=0, cr=0, acc=0, trig=0),
        Encoder(wenc=200, ttl_linerate_cyc=6, reserve=2, xenc=2000,
                unwrapping_number=4, reserve2=1, cr=1, acc=0, trig=0),
        Encoder(wenc=300, ttl_linerate_cyc=7, reserve=3, xenc=3000,
                unwrapping_number=5, reserve2=2, cr=0, acc=1, trig=1),
    ]


def _make_image() -> np.ndarray:
    return np.arange(30, dtype=np.uint16).reshape(3, 10) + 100


# ── tests ────────────────────────────────────────────────────────────

def test_basic_roundtrip():
    """Generate file → parse → assert all fields match."""
    head = _make_header()
    footer = _make_footer()
    encoders = _make_encoders()
    img = _make_image()
    path = os.path.join(tempfile.gettempdir(), "_test_pkt8M.tt")

    build_test_file(path, head, footer, encoders, img)
    pkt = load_packet8M(path)

    # Header
    assert pkt.head.packet_id == 42
    assert pkt.head.sensor_width == 10
    assert pkt.head.line_info_enable == 0
    assert pkt.head.reserve2 == b"\x00" * 32

    # Footer
    assert pkt.footer.check_sum == 0xABCDEF
    assert pkt.footer.valid_line == 3
    assert pkt.footer.packet_end == 0xABAB

    # Data
    assert pkt.data.shape == (3, 10)
    assert np.array_equal(pkt.data, img)

    # Encoder
    assert len(pkt.encoder) == 3
    assert pkt.encoder[0].wenc == 100
    assert pkt.encoder[0].xenc == 1000
    assert pkt.encoder[1].wenc == 200
    assert pkt.encoder[1].cr == 1
    assert pkt.encoder[2].trig == 1
    assert pkt.encoder[2].acc == 1

    # Lineinfo
    assert pkt.lineinfo is None

    os.remove(path)
    print("  test_basic_roundtrip  PASSED")


def test_size_mismatch():
    """File of wrong size should raise ValueError."""
    path = os.path.join(tempfile.gettempdir(), "_test_bad.tt")
    with open(path, "wb") as f:
        f.write(b"\x00" * 100)
    try:
        load_packet8M(path)
        assert False, "Expected ValueError"
    except ValueError:
        pass
    os.remove(path)
    print("  test_size_mismatch    PASSED")


def test_lineinfo():
    """File with line_info_enable=1 should return lineinfo data."""
    head = _make_header()
    head.line_info_enable = 1
    footer = _make_footer()
    encoders = _make_encoders()
    img = _make_image()
    li = np.arange(3 * 96, dtype=np.uint8).reshape(3, 96)
    path = os.path.join(tempfile.gettempdir(), "_test_pkt8M_li.tt")

    build_test_file(path, head, footer, encoders, img, lineinfo=li)
    pkt = load_packet8M(path)

    assert pkt.lineinfo is not None
    assert pkt.lineinfo.shape == (3, 96)
    assert np.array_equal(pkt.lineinfo, li)

    os.remove(path)
    print("  test_lineinfo         PASSED")


if __name__ == "__main__":
    test_basic_roundtrip()
    test_size_mismatch()
    test_lineinfo()
    print("\nAll tests passed.")
