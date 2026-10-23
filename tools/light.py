"""Light tiles or LED ranges for a while, to test the board without the web app.

Tiles use the same numbers as the web app (1-47). LED ranges use raw LED numbers (0-1409),
which is handy when checking wiring. Nothing is saved on the board.

Usage:
  python tools/light.py 5 12 40                      tiles 5, 12, 40 in purple for 20 s
  python tools/light.py 5 12 --color red --seconds 60
  python tools/light.py --leds 0-29:red 30-59:blue   LED ranges, each in its own color
  python tools/light.py 1 --ip 10.0.0.42             another panel (e.g. the Valiant Living one)
"""
import argparse

import wled

parser = argparse.ArgumentParser(description="Light tiles or LED ranges on the hex panel.")
parser.add_argument("tiles", nargs="*", type=int, help="tile numbers, 1-47")
parser.add_argument("--color", default="purple", help="color name or hex code (default purple)")
parser.add_argument("--leds", nargs="*", default=[], metavar="RANGE:COLOR", help="e.g. 0-29:red 75:white")
parser.add_argument("--seconds", type=float, default=20)
parser.add_argument("--ip", help="board address (default: wledIp in config.json)")
args = parser.parse_args()

if not args.tiles and not args.leds:
    parser.error("give at least one tile number or --leds range")

frame = wled.blank_frame()

# 1. tiles, in one color
for tile in args.tiles:
    if not 1 <= tile <= wled.NUM_TILES:
        parser.error(f"tile {tile} is outside 1-{wled.NUM_TILES}")
    wled.paint(frame, wled.leds_of_pos(wled.chain_pos(tile)), wled.color(args.color))

# 2. raw LED ranges, each in its own color
for spec in args.leds:
    rng, col = spec.split(":")
    first, _, last = rng.partition("-")
    wled.paint(frame, range(int(first), int(last or first) + 1), wled.color(col))

print(f"lighting for {args.seconds:.0f} s (Ctrl + C to stop early)")
try:
    wled.stream(frame, args.seconds, args.ip)
except KeyboardInterrupt:
    pass
print("stopped, the board goes back to its own effect in ~2.5 s")
