# board tools

Small Python scripts for testing the hex panel straight from a laptop, without starting the web app. I used them to learn how the board works, and to find a melted wire on wire 1 in October 2026. They are meant for anyone who has to check the hardware later: after moving the panel, after a repair, or when setting up the second panel at Valiant Living.

Nothing here changes the board's settings. The light tools use WLED's live mode (the board shows our frames while they keep coming and goes back to its own effect ~2.5 s after they stop), and `check_board.py` only reads.

## what you need

- Python 3.8 or newer. No packages to install.
- A computer on the same network as the board.
- The board's address in `config.json` (`wledIp`). The tools read it from there, the same file the web app uses. For another panel, add `--ip <address>`.

## what's where

```
tools/
  check_board.py    read-only health check: LED count, wiring, presets file, power limiter, firmware lock
  light.py          light tiles (same numbers as the web app) or raw LED ranges, in any color
  walk_chain.py     light one wire hex by hex in chain order, to find where a signal stops
  wled.py           shared code: reads config.json, builds frames, sends them over DDP
```

## how to use them

Run them from the repo folder (the one with `config.json`):

```
python tools/check_board.py
python tools/light.py 5 12 40
python tools/light.py 5 12 --color red --seconds 60
python tools/light.py --leds 0-29:red 30-59:blue
python tools/walk_chain.py 1
```

- Ctrl + C stops a light tool early.
- Colors: `red green blue purple yellow cyan orange pink white lime sky magenta teal gold violet coral`, or a hex code like `FF0080`. The named colors are medium brightness on purpose.
- Every script has `--help`.

## how the board is laid out

- 47 hexes, 30 LEDs each, 1410 LEDs. Inside a hex, the LEDs run clockwise.
- Three wires (LED outputs on the controller), one per color group in the web app:

  | wire | pin | LEDs | chain positions | web app group |
  |---|---|---|---|---|
  | 1 | GPIO 16 | 0-479 | 0-15 | red, 16 hexes |
  | 2 | GPIO 3 | 480-929 | 16-30 | green, 15 hexes |
  | 3 | GPIO 1 | 930-1409 | 31-46 | blue, 16 hexes |

- Tile numbers (what you see in the web app) and chain positions (where a hex is on the wire) are almost the same. `map` in `config.json` connects them, and the tools use it, so tile 5 in a tool is tile 5 on the screen.

## why DDP and not the web app's UDP format

The web app sends animation frames as WLED "DNRGB" packets on port 21324. These tools use DDP on port 4048. Both are WLED live modes and both work. DDP was simply what I tested first, and it needs no setting on the board. If the team settles on one format, `stream()` in `wled.py` is the only function to change.

## safety

- WLED's power limiter is currently off (`check_board.py` warns about it). Keep effects at medium brightness and avoid lighting the whole board in white.
- Wire 1 has melted once already. After any repair, run `walk_chain.py 1` and watch the repaired spot for heat or a burnt smell.
- Turn the power off before touching any wiring.
