"""Read-only health check of the board. It only reads from WLED, it never changes anything.

I added this after finding problems by accident that a quick check would have caught:
the presets file was broken (the WLED page said "issue loading your presets"),
the power limiter was off, and anyone on the network could update the firmware.

Checks:
  1. the board answers, and its LED count matches config.json,
  2. the three LED outputs match the wires the tools expect,
  3. presets.json is valid JSON,
  4. the power limiter is on,
  5. the firmware update lock is on.

Usage:  python tools/check_board.py  [--ip 10.0.0.42]
"""
import argparse
import json
import sys
import urllib.request

import wled

parser = argparse.ArgumentParser(description="Read-only health check of the hex panel board.")
parser.add_argument("--ip", default=wled.CONFIG["wledIp"])
args = parser.parse_args()


def get(path):
    with urllib.request.urlopen(f"http://{args.ip}{path}", timeout=5) as r:
        return r.read().decode("utf-8", errors="replace")


problems, warnings = [], []

# 1. board answers
try:
    info = json.loads(get("/json/info"))
    cfg = json.loads(get("/json/cfg"))
except Exception as e:
    sys.exit(f"cannot reach the board at {args.ip}: {e}")
print(f"ok  {info['name']} at {args.ip}, WLED {info['ver']}, {info['leds']['count']} LEDs, "
      f"Wi-Fi signal {info['wifi']['signal']}%")
if info["leds"]["count"] != wled.NUM_LEDS:
    problems.append(f"board has {info['leds']['count']} LEDs, config.json expects {wled.NUM_LEDS}")

# 2. LED outputs vs. wires
outputs = cfg["hw"]["led"]["ins"]
for wire, out in zip(sorted(wled.WIRES), outputs):
    expect = wled.WIRES[wire]
    first, count = out["start"], out["len"]
    print(f"ok  wire {wire}: pin {out['pin'][0]}, LEDs {first}-{first + count - 1}")
    if first != wled.LED_OFFSET + expect.start * wled.LEDS_PER_HEX or count != len(expect) * wled.LEDS_PER_HEX:
        problems.append(f"wire {wire} does not match WIRES in tools/wled.py")

# 3. presets
try:
    presets = json.loads(get("/presets.json"))
    print(f"ok  presets.json ({len(presets)} presets)")
except json.JSONDecodeError as e:
    problems.append(f"presets.json is broken ({e}). Back it up before editing presets.")

# 4. power limiter (0 mA = off)
if cfg["hw"]["led"].get("maxpwr", 0) == 0 or info["leds"].get("maxpwr", 0) == 0:
    warnings.append("power limiter is off: bright effects can draw more current than the wiring handles")

# 5. firmware update lock
if not cfg.get("ota", {}).get("lock", False):
    warnings.append("firmware update lock is off: anyone on the network can reflash the board")

for w in warnings:
    print(f"warn  {w}")
if problems:
    print("\nSomething is off:\n  " + "\n  ".join(problems))
    sys.exit(1)
print("\nNo problems found." + (" (see warnings above)" if warnings else ""))
