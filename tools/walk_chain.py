"""Light one wire's hexes one after another, in the order they sit on the LED chain.

I wrote this to find a wiring fault: on 2026-10-14 only the first hex of wire 1 lit up and the
rest stayed dark, because a wire had melted after it. Walking the chain shows exactly where the
signal stops. It also prints which tile each chain position is, so it doubles as a mapping check.

Usage:
  python tools/walk_chain.py 1                 wire 1, a new hex every 3 s, then hold 30 s
  python tools/walk_chain.py 3 --step 5 --hold 60
"""
import argparse

import wled

parser = argparse.ArgumentParser(description="Walk one wire of the hex panel, hex by hex.")
parser.add_argument("wire", type=int, choices=sorted(wled.WIRES))
parser.add_argument("--step", type=float, default=3, help="seconds per hex (default 3)")
parser.add_argument("--hold", type=float, default=30, help="seconds to hold at the end (default 30)")
parser.add_argument("--ip", help="board address (default: wledIp in config.json)")
args = parser.parse_args()

names = list(wled.COLORS)
frame = wled.blank_frame()

try:
    for n, pos in enumerate(wled.WIRES[args.wire]):
        name = names[n % len(names)]
        wled.paint(frame, wled.leds_of_pos(pos), wled.COLORS[name])
        leds = wled.leds_of_pos(pos)
        print(f"wire {args.wire}  hex {n + 1:2}  chain pos {pos:2}  tile {wled.tile_at(pos):2}  "
              f"LEDs {leds.start}-{leds.stop - 1}  {name}", flush=True)
        wled.stream(frame, args.step, args.ip)
    print(f"all lit, holding {args.hold:.0f} s")
    wled.stream(frame, args.hold, args.ip)
except KeyboardInterrupt:
    pass
print("stopped, the board goes back to its own effect in ~2.5 s")
