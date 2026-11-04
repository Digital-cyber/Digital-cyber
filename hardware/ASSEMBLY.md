# ASSEMBLY — enclosure build (Tier 1)

A finished, carryable HID token: XIAO RP2040 + 4 panel-mount buttons + a status
LED in a project box, with a clean external USB-C port. No PCB fab required.

This is the "buy-now" build. For the custom-PCB version see `pcb/DESIGN.md`.

---

## Pin map (matches the firmware)

| Signal | XIAO pin | Goes to |
|--------|----------|---------|
| MODE button | `D0` | button leg → D0, other leg → GND |
| KEY 1 | `D1` | button leg → D1, other leg → GND |
| KEY 2 | `D2` | button leg → D2, other leg → GND |
| KEY 3 | `D3` | button leg → D3, other leg → GND |
| STATUS LED (+) | `D6` | D6 → 330Ω → LED anode; LED cathode → GND |
| Ground | `GND` | common rail for all buttons + LED cathode |
| USB | USB-C | short C–C cable to the panel USB-C jack |

Buttons use the RP2040's internal pull-ups (pressed = pin pulled to GND), so
**no resistors on the buttons**. The only resistor is the 330Ω for the LED.

> Onboard LEDs also light (green solid = keyboard, blue blink = drive) but they
> live *inside* the box — the external D6 LED is what you'll actually see:
> **solid = keyboard mode, blinking = drive mode.**

---

## Bill of materials

| Qty | Part | Notes |
|-----|------|-------|
| 1 | XIAO RP2040 (pre-soldered recommended) | the brain |
| 4 | 12mm **momentary** panel-mount buttons | NOT latching; pre-wired saves effort |
| 1 | 5mm panel-mount LED (any color) | mode indicator |
| 1 | 330Ω resistor (⅛–¼ W) | LED current limit |
| 1 | USB-C panel pass-through (data-capable, 10Gbps/USB3.x) | external port |
| 1 | short USB-C ↔ USB-C cable | jack → XIAO, kept inside |
| 1 | ABS project box (~100×60×25mm or larger) | enclosure |
| — | perfboard scrap, 22–24AWG wire, heat-shrink, solder | wiring |
| — | M2 standoffs/screws or hot glue | anchor the board |

---

## Panel layout & drill template

```
   TOP FACE (buttons + LED)                 END FACE (port)
   ┌───────────────────────────┐           ┌───────────────┐
   │   (K1)     (K2)     (K3)   │           │               │
   │    O        O        O     │           │   [=USB-C=]    │
   │                            │           │               │
   │          (LED)             │           └───────────────┘
   │           o                │
   │      (MODE, recessed)      │     Hole sizes:
   │           O                │       K1/K2/K3/MODE : 12mm
   └───────────────────────────┘       LED            : 5–6mm (to fit holder)
                                        USB-C jack     : per jack (often ~11×7mm
   Spacing: ~18–20mm between 12mm                        rectangle or a round
   buttons so the nuts don't collide.                    keystone cutout)
```

Mark centers, start with a small pilot bit, step up to final size. ABS drills
easily — go slow near final size so it doesn't crack. Deburr the holes.

---

## Build order

1. **Flash first, assemble second.** Put firmware on the XIAO while it's still
   easy to reach the BOOT/RESET buttons (see repo `hid-token/README.md` →
   Flashing, or use `hid-token/deploy/`). Confirm it types before you box it up.
2. **Drill** the top face (4×12mm + LED) and the end face (USB-C).
3. **Mount hardware** in the panel: the 4 buttons, the LED holder, the USB-C
   pass-through. Tighten their nuts.
4. **Prep the XIAO** on a small perfboard scrap (solder it down, or socket it).
   Bring out wires for D0, D1, D2, D3, D6, GND, and the USB-C.
5. **Wire the grounds:** daisy-chain one leg of every button + the LED cathode
   to a single GND wire back to the XIAO `GND`. (Twist/solder a common rail.)
6. **Wire the signals:** each button's other leg → its D-pin (D0/D1/D2/D3).
7. **Wire the LED:** `D6 → 330Ω → LED(+)`, `LED(−) → GND`.
8. **USB-C:** short C–C cable from the panel jack to the XIAO's USB-C.
9. **Anchor** the perfboard with standoffs or a dab of hot glue so nothing
   flexes against the USB connector.
10. **Close it up.**

---

## Smoke test (before final close)

- [ ] Plug in → **LED solid** (keyboard mode). Focus a text field, press K1/K2/K3
      → the matching `keys.txt` line types.
- [ ] Press **MODE** → board reboots, **LED starts blinking** (drive mode), the
      drive mounts → you can edit `keys.txt`.
- [ ] Press **MODE** again → back to solid, typing works.
- [ ] Wiggle the USB-C cable — no disconnects (anchor if it's flaky).

---

## Soldering & reliability notes

- **Strain-relief the USB-C.** The single most common failure is the USB
  connector tearing loose. Anchor the board and don't let the internal cable
  pull on it.
- **Keep button wires short and twisted** to avoid snagging when you close the
  lid.
- **Label each board** (K1/K2/K3 purpose) — in a lab you'll forget which creds
  are on which unit.
- **Heat-shrink every exposed solder joint**; a project box is a tight tangle.

## Confidence notes

- Pin choices (D0–D3, D6, GND) match the committed firmware and are all broken
  out on the XIAO RP2040. **Confidence: high.**
- Box size 100×60×25mm comfortably holds the XIAO + a perfboard scrap + wiring;
  with 4×12mm buttons on top you want the lid area, so verify the internal
  depth clears the button bodies + nuts (~15mm) before buying a shallower box.
  **Confidence: medium** — depends on the exact button body length.
- USB-C panel parts vary in cutout shape (keystone vs threaded round). Match the
  drill to the specific jack you buy. **Confidence: medium.**
