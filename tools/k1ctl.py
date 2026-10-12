#!/usr/bin/env python3
"""Live VFO control for UV-K1 / UV-K5 V3 firmware (command 0x0531).

USB CDC ignores baud. The programming connector is 38400 8N1.
"""

import argparse
import sys

try:
    import serial
except ImportError:
    serial = None

OBF = bytes([
    0x16, 0x6C, 0x14, 0xE6, 0x2E, 0x91, 0x0D, 0x40,
    0x21, 0x35, 0xD5, 0x40, 0x13, 0x03, 0xE9, 0x80,
])

MODES = {
    "FM": 0,
    "AM": 1,
    "USB": 2,
    "CW": 3,
}
MODE_NAMES = {value: name for name, value in MODES.items()}

BANDWIDTHS = {
    "WIDE": 0,
    "NARROW": 1,
}
BW_NAMES = {value: name for name, value in BANDWIDTHS.items()}

STATUS = {
    0: "ok",
    1: "bad VFO index",
    2: "frequency out of band",
    3: "radio is transmitting",
    4: "modulation not built into this firmware",
    5: "bad bandwidth",
}


def crc16(data: bytes) -> int:
    crc = 0
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc


def frame(payload: bytes) -> bytes:
    mixed = bytes(b ^ OBF[i % 16] for i, b in enumerate(payload))
    c = crc16(payload)
    crc_bytes = bytes([c & 0xFF, (c >> 8) & 0xFF])
    mixed_crc = bytes(b ^ OBF[(len(payload) + i) % 16] for i, b in enumerate(crc_bytes))
    length = len(payload).to_bytes(2, "little")
    return b"\xAB\xCD" + length + mixed + mixed_crc + b"\xDC\xBA"


def set_vfo(vfo: int, hz: int, modulation: int, bandwidth: int) -> bytes:
    body = (
        bytes([vfo])
        + hz.to_bytes(4, "little")
        + bytes([modulation & 0xFF, bandwidth & 0xFF])
    )
    payload = (0x0531).to_bytes(2, "little") + len(body).to_bytes(2, "little") + body
    return frame(payload)


def parse_reply(raw: bytes):
    start = raw.find(b"\xAB\xCD")
    if start < 0 or len(raw) < start + 8:
        return None
    size = int.from_bytes(raw[start + 2:start + 4], "little")
    end = start + 4 + size + 2
    if len(raw) < end + 2 or raw[end:end + 2] != b"\xDC\xBA":
        return None
    mixed = raw[start + 4:end]
    plain = bytes(b ^ OBF[i % 16] for i, b in enumerate(mixed))
    payload, crc_got = plain[:-2], int.from_bytes(plain[-2:], "little")
    if crc16(payload) != crc_got:
        raise SystemExit("reply CRC mismatch")
    if int.from_bytes(payload[:2], "little") != 0x0532 or len(payload) < 10:
        return None
    status = payload[4]
    vfo = payload[5]
    hz = int.from_bytes(payload[6:10], "little")
    modulation = payload[10] if len(payload) >= 12 else None
    bandwidth = payload[11] if len(payload) >= 12 else None
    return status, vfo, hz, modulation, bandwidth


def main() -> int:
    ap = argparse.ArgumentParser(description="Set the live VFO over USB serial")
    ap.add_argument("--port", "-p", required=True)
    ap.add_argument("--baud", type=int, default=115200)
    ap.add_argument("--vfo", type=int, choices=(0, 1), default=0)
    ap.add_argument("--mod", choices=tuple(MODES), default=None,
                    help="FM, AM, USB, or CW; omit to keep the current mode")
    ap.add_argument("--bw", choices=tuple(BANDWIDTHS), default=None,
                    help="WIDE or NARROW; omit to keep the current bandwidth")
    ap.add_argument("mhz", nargs="?", help="frequency in MHz, e.g. 145.5; omit to keep it")
    args = ap.parse_args()

    if args.mhz is None and args.mod is None and args.bw is None:
        ap.error("give a frequency, --mod, or --bw")

    if serial is None:
        sys.exit("pyserial is missing. Create the virtual environment described in README.md")

    # Radio frequency unit is 10 Hz (145.5 MHz -> 14550000), same as the keypad.
    # 0xFFFFFFFF tells the radio to leave the current frequency alone.
    hz = 0xFFFFFFFF if args.mhz is None else int(round(float(args.mhz) * 100_000))
    mod = 0xFF if args.mod is None else MODES[args.mod]
    bw = 0xFF if args.bw is None else BANDWIDTHS[args.bw]
    packet = set_vfo(args.vfo, hz, mod, bw)

    with serial.Serial(args.port, args.baud, timeout=1) as ser:
        ser.write(packet)
        reply = parse_reply(ser.read(64))

    if reply is None:
        sys.exit("no 0x0532 reply (flash a firmware that includes the live VFO command)")
    status, vfo, applied, modulation, bandwidth = reply
    mode = MODE_NAMES.get(modulation, "?" if modulation is None else str(modulation))
    width = BW_NAMES.get(bandwidth, "?" if bandwidth is None else str(bandwidth))
    print(f"VFO {vfo}  {applied / 100_000:.5f} MHz  {mode}  {width}  {STATUS.get(status, status)}")
    return 0 if status == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
