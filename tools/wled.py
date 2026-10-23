"""Shared helpers for the board tools: read config.json, build a frame, send it to WLED.

Every tool sends frames the same way, so the protocol lives here once.
Frames go over DDP (UDP port 4048), WLED's live mode. WLED shows them while they keep
coming and falls back to its own effect ~2.5 s after the last one, so nothing is saved on the board.
"""
import json
import socket
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))

NUM_TILES = 47
LEDS_PER_HEX = CONFIG["ledsPerHex"]
LED_OFFSET = CONFIG["ledOffset"]
NUM_LEDS = LED_OFFSET + NUM_TILES * LEDS_PER_HEX
DDP_PORT = 4048

# wire = one LED output on the controller; the order inside each wire is its chain position
WIRES = {1: range(0, 16), 2: range(16, 31), 3: range(31, 47)}

# medium brightness on purpose: the power limiter is off and one wire has already melted once
COLORS = {
    "red": (192, 0, 0), "green": (0, 192, 0), "blue": (0, 0, 192), "purple": (128, 0, 192),
    "yellow": (192, 144, 0), "cyan": (0, 160, 160), "orange": (192, 64, 0), "pink": (192, 0, 96),
    "white": (128, 128, 128), "lime": (96, 192, 0), "sky": (0, 96, 192), "magenta": (192, 0, 192),
    "teal": (0, 128, 64), "gold": (160, 100, 0), "violet": (64, 0, 192), "coral": (192, 48, 48),
}


def color(text):
    """'purple' or a hex code like 'FF0080' -> (r, g, b)."""
    if text.lower() in COLORS:
        return COLORS[text.lower()]
    h = text.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def chain_pos(tile):
    """Tile number as shown in the web app (1-47) -> its position on the LED chain (0-46)."""
    return CONFIG["map"][tile - 1]


def tile_at(pos):
    """The reverse: chain position -> tile number."""
    return CONFIG["map"].index(pos) + 1


def leds_of_pos(pos):
    start = LED_OFFSET + pos * LEDS_PER_HEX
    return range(start, start + LEDS_PER_HEX)


def blank_frame():
    return bytearray(NUM_LEDS * 3)


def paint(frame, leds, rgb):
    for led in leds:
        frame[led * 3:led * 3 + 3] = bytes(rgb)


def stream(frame, seconds, ip=None, fps=20):
    """Send the same frame again and again for `seconds`. Ctrl + C stops early."""
    ip = ip or CONFIG["wledIp"]
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    chunk = 480 * 3  # one packet holds at most 480 LEDs
    end = time.time() + seconds
    while time.time() < end:
        for off in range(0, len(frame), chunk):
            data = frame[off:off + chunk]
            last = off + chunk >= len(frame)
            # 10-byte DDP header: version 1 (+ "show now" on the last packet), RGB data, offset, length
            header = bytes([0x41 if last else 0x40, 0, 0x0B, 0x01]) + off.to_bytes(4, "big") + len(data).to_bytes(2, "big")
            sock.sendto(header + data, (ip, DDP_PORT))
        time.sleep(1 / fps)
