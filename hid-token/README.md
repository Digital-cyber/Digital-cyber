# hid-token — button-press password typer (Seeed XIAO RP2040)

A tiny USB device with **two physical buttons**:

- **PASSWORD button** — types a stored secret as if you typed it on a keyboard (USB HID).
- **MODE button** — live-toggles the device's USB identity between **KEYBOARD** and **DRIVE** (plain USB mass-storage). Pressing it reboots the board (~1–2s) and it re-enumerates as the other device.

Chip is the **RP2040** — same silicon as a Raspberry Pi Pico, so this ports straight across from a Pico/"Pi micro" build.

---

## How the mode switch actually works

USB identity is fixed **at enumeration** (power-on), so you can't cleanly morph a live device from drive → keyboard. The trick here:

```
   PASSWORD btn (D1)                 MODE btn (D0)
        │                                │
        ▼                                ▼
   ┌─────────────────────────────────────────────┐
   │  code.py  (runs in both modes)               │
   │    pass press  → type /secret.txt  (HID only)│
   │    mode press  → nvm[0] ^= 1 ; reset()       │
   └───────────────────────┬─────────────────────┘
                           │  (soft reset)
                           ▼
   ┌─────────────────────────────────────────────┐
   │  boot.py  reads nvm[0]                        │
   │    1 → KEYBOARD: HID on, drive hidden         │
   │    0 → DRIVE:    plain USB stick, no HID       │
   └─────────────────────────────────────────────┘
```

The mode is stored in **microcontroller NVM** (one byte), not a file — because in DRIVE mode the *host* owns the filesystem and the firmware can't write to it. NVM survives reset and power loss.

**Stuck?** Hold the **MODE button while plugging in** to force-flip the stored mode at boot.

---

## Bill of materials (Amazon)

> I couldn't open Amazon listing pages directly, so treat prices/stock as approximate — verify before buying. Search terms + a known ASIN are given so you land on the right part.

| # | Part | What to search / ID | ~Price | Notes |
|---|------|--------------------|--------|-------|
| 1 | **Seeed Studio XIAO RP2040** | ASIN **B09NNVNW7M** ("Seeed Studio XIAO RP2040") | ~$8–10 | The board. Dual-core M0+, 2MB flash, USB-C. |
| 2 | **Tactile momentary push buttons** | "QTEATAK 20pcs 6mm tactile push button" (through-hole, breadboard-friendly) | ~$7 | You need 2; buy a pack. 4-pin 6mm are everywhere. |
| 3 | **USB-C *data* cable** | "USB-C data cable short" | ~$6 | ⚠️ Must be a **data** cable, not charge-only — #1 beginner gotcha. |
| 4 | **Half/solderless breadboard + jumper wires** (prototype) | "breadboard jumper wire kit" | ~$8 | For testing before you commit to solder. |

**Optional / nicer build:**

| Part | Search | Why |
|------|--------|-----|
| Panel-mount momentary buttons (12mm) | "12mm momentary push button panel mount" | Real clicky feel if you case it. |
| Mini perfboard / protoboard | "1x2 inch perfboard" | Solder it down for a permanent token. |
| Small project enclosure | "mini project box 50mm" | Turn it into a keyfob-style device. |
| Soldering iron + solder | "soldering iron kit" | If you don't already have one. |

You only strictly need **#1 + #2 + #3** to have a working device (buttons can even be momentarily jumpered by hand to test).

---

## Wiring

XIAO RP2040 has internal pull-ups, so each button just shorts a pin to GND. No resistors needed.

```
        XIAO RP2040 (USB-C at top)
        ┌───────────────┐
        │ D0 ........... │  ── MODE button ── GND
        │ D1 ........... │  ── PASSWORD button ── GND
        │ ...           │
        │ GND           │  ── (common ground rail)
        └───────────────┘

   Each button: one leg to the signal pin (D0 / D1),
                the diagonally-opposite leg to GND.
```

(On a 4-pin tactile switch, the two legs on the *same side* are shorted internally — use legs that are diagonal to each other to be safe.)

---

## Flashing (CircuitPython)

1. **Install CircuitPython** on the XIAO RP2040:
   - Download the XIAO RP2040 `.uf2` from circuitpython.org/downloads.
   - Hold **B(OOT)** on the board, tap **R(ESET)** (or plug in while holding BOOT) → a drive named `RPI-RP2` appears.
   - Drag the `.uf2` onto it. It reboots as a drive named **CIRCUITPY**.
2. **Add the HID library:**
   - Download the CircuitPython **library bundle** (matching your CP major version) from circuitpython.org/libraries.
   - Copy the **`adafruit_hid`** folder into `CIRCUITPY/lib/`.
3. **Copy these files** to the root of `CIRCUITPY`:
   - `boot.py`, `code.py`, `secret.txt`
4. **Edit `secret.txt`** — put your password on the first line (no quotes).
5. Eject/replug. It boots in **DRIVE** mode the very first time; press **MODE** to flip to **KEYBOARD**, then press **PASSWORD** on a focused text field to confirm.

> The `lib_placeholder/` folder in this repo is just a reminder — the real `adafruit_hid` library is not committed (it belongs to Adafruit and tracks your CircuitPython version).

---

## Security / opsec notes (read before trusting it with a real password)

- **`secret.txt` is plaintext.** Hiding the drive in KEYBOARD mode stops *casual* mounting, but anyone who can dump the RP2040 flash can read it. A bare RP2040 has **no secure element**.
- **Raise the bar (in rough order of effort):**
  - Keep it in KEYBOARD mode so the drive isn't mounted by default (already the behavior).
  - Obfuscate the stored value (e.g. XOR with a key). *Obfuscation ≠ encryption* — it slows a curious person, not a determined one.
  - For secrets that actually matter: use a board with a secure element (e.g. nRF52840 + ATECC608) or require a PIN typed on more buttons before the secret is released.
- **Keyboard layout:** `KeyboardLayoutUS` sends **US** scancodes. If the target host uses another layout, symbols come out wrong. Keep passwords to `[A-Za-z0-9]` or add the matching layout library.
- **No keystrokes fire on plug-in** — typing is gated behind the physical button. That's deliberate: fewer "why did my PC just type something" surprises, and it keeps this a *you-initiated* tool.

---

## Files

| File | Role |
|------|------|
| `boot.py` | Chooses USB identity at enumeration from the NVM mode byte. |
| `code.py` | Main loop: password-typing + live mode toggle via soft reset. |
| `secret.txt` | The string typed on the PASSWORD button. **Edit this.** |

## Sources

- [Seeed XIAO RP2040 (The Pi Hut)](https://thepihut.com/products/seeed-xiao-rp2040) · [specs mirror, ASIN B09NNVNW7M](https://specpicks.com/product/B09NNVNW7M) · [Seeed XIAO RP2040 getting started](https://how2electronics.com/getting-started-with-seeed-xiao-rp2040-with-projects/)
- [12mm tactile switch buttons (The Pi Hut)](https://thepihut.com/collections/all/products/tactile-switch-buttons-12mm-square-6mm-tall-x-10-pack) · [200-pc 6mm button kit (ShillehTek)](https://shillehtek.com/products/200pcs-6mm-light-touch-button-switch-kit-plastic-box-4-3-5-6-7-8-9-10-12-14-16mm)
