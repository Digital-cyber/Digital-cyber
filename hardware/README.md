# hardware — finished-product builds for the HID token

Two ways to turn the `hid-token/` firmware into a real, enclosed device:

- **[`ASSEMBLY.md`](ASSEMBLY.md) — Tier 1: enclosure build.** XIAO + panel-mount
  buttons + status LED in a project box. Buy-now, no PCB fab. Done in an evening.
- **[`pcb/DESIGN.md`](pcb/DESIGN.md) — Tier 2: custom PCB.** A small 2-layer
  carrier board for the polished v2. Design spec + fab/order steps (recreate in
  KiCad or hand to a layout service).

Both use the same firmware and the same pin map:

| MODE | KEY1 | KEY2 | KEY3 | STATUS LED |
|------|------|------|------|------------|
| D0 | D1 | D2 | D3 | D6 (→330Ω→LED→GND) |

**LED tells you the mode at a glance:** solid = keyboard, blinking = drive.

---

## Shopping list (US Amazon) — Tier 1

> Prices approximate (search didn't return live prices); verify on the page.
> You need the buttons to be **MOMENTARY, not latching**, and the USB-C panel
> part to be **data-capable (10Gbps / USB 3.x)**.

| Part | Link | ~Price |
|------|------|--------|
| XIAO RP2040 (pre-soldered) | [dp/B0DRNTQ338](https://www.amazon.com/Seeed-Studio-XIAO-RP2040-Pre-Soldered/dp/B0DRNTQ338) | ~$9–13 |
| 12mm metal momentary buttons ×4 | [uxcell 12mm](https://www.amazon.com/uxcell-Momentary-Button-Switch-Mounting/dp/B08HHZCPGN) · [stainless](https://www.amazon.com/Momentary-Stainless-Housing-Electronics-Controls/dp/B0H2MD1FZW) · [browse](https://www.amazon.com/12mm-momentary-switch/s?k=12mm+momentary+switch) | ~$2–4 ea |
| ABS project box ~100×60×25mm | [dp/B0H67KWVJ7](https://www.amazon.com/Plastic-Electronic-Project-Box-Enclosure/dp/B0H67KWVJ7) | ~$7 |
| USB-C panel pass-through (data) | [keystone 10Gbps](https://amazon.com/Keystone-Extention-Keystone-Convertor-Extension/dp/B08GSQ13C8) | ~$9 |
| Perfboard kit | [ELEGOO 32pc](https://www.amazon.com/clp/B072Z7Y19F) | ~$10 |
| 5mm panel LED + 330Ω resistor | [browse panel LEDs](https://www.amazon.com/s?k=5mm+panel+mount+LED+holder) · [browse resistor kit](https://www.amazon.com/s?k=330+ohm+resistor+kit) | ~$8 |

Plus consumables you may already own: soldering iron + solder, 22–24AWG wire,
heat-shrink, M2 standoffs/screws.

**Tier 1 total ≈ $45–60.** Tier 2 adds ~$2–15 for 5 PCBs (+ ~1–2 wk lead).

*Sources:* [XIAO RP2040 pre-soldered](https://www.amazon.com/Seeed-Studio-XIAO-RP2040-Pre-Soldered/dp/B0DRNTQ338), [12mm momentary (uxcell)](https://www.amazon.com/uxcell-Momentary-Button-Switch-Mounting/dp/B08HHZCPGN), [12mm momentary (stainless)](https://www.amazon.com/Momentary-Stainless-Housing-Electronics-Controls/dp/B0H2MD1FZW), [ABS box](https://www.amazon.com/Plastic-Electronic-Project-Box-Enclosure/dp/B0H67KWVJ7), [USB-C keystone](https://amazon.com/Keystone-Extention-Keystone-Convertor-Extension/dp/B08GSQ13C8), [ELEGOO perfboard](https://www.amazon.com/clp/B072Z7Y19F).
