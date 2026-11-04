# hid-token — rapid-deploy button password typer (Seeed XIAO RP2040)

A tiny USB device for **lab work**: plug it in and fire stored credentials from physical buttons. No PIN, no fuss — **keys in hand the moment it's plugged in**.

- **KEY buttons (D1 / D2 / D3)** — each types a line from `keys.txt` as if typed on a keyboard (USB HID). D1→line 1, D2→line 2, D3→line 3.
- **MODE button (D0)** — only needed to drop to a **plain USB drive** so you can edit `keys.txt`. Press it again to go back to keyboard.

**Boots straight into KEYBOARD mode**, so a freshly flashed board is ready to type immediately. Chip is the **RP2040** — same as a Pi Pico, so it ports straight across from a Pico/"Pi micro" build.

---

## How it works

USB identity is fixed **at enumeration** (power-on), so you can't morph a live device drive→keyboard. The MODE button flips a persisted **NVM byte** and soft-resets; `boot.py` re-reads it and presents the new identity (~1–2s).

```
   KEY btns (D1/D2/D3)              MODE btn (D0)
        │                               │
        ▼                               ▼
   ┌─────────────────────────────────────────────┐
   │  code.py  (runs in both modes)               │
   │    key press  → type keys.txt line (HID only)│
   │    mode press → nvm[0] ^= 1 ; reset()        │
   └───────────────────────┬─────────────────────┘
                           │  (soft reset)
                           ▼
   ┌─────────────────────────────────────────────┐
   │  boot.py reads nvm[0]  (default = KEYBOARD)  │
   │    1 → KEYBOARD: HID on, drive hidden         │
   │    0 → DRIVE:    editable USB stick, no HID    │
   └─────────────────────────────────────────────┘
```

Mode lives in **NVM** (one byte), not a file — in DRIVE mode the *host* owns the filesystem so the firmware can't write there. NVM survives reset and power loss.

**Stuck in the wrong mode?** Hold **MODE while plugging in** to force-flip at boot.

**More keys?** Wire another button and add its pin to `KEY_PIN_NAMES` in `code.py` — it maps to the next line of `keys.txt` automatically.

---

## Bill of materials (Amazon)

> I couldn't open Amazon pages directly — treat prices/stock as approximate and verify before buying. Search terms + a known ASIN get you to the right part.

| # | Part | Search / ID | ~Price | Notes |
|---|------|-------------|--------|-------|
| 1 | **Seeed Studio XIAO RP2040** | ASIN **B09NNVNW7M** | ~$8–10 | The board. USB-C, thumb-sized. |
| 2 | **6mm tactile push buttons** | "QTEATAK 20pcs 6mm tactile push button" | ~$7 | Need up to **4** (1 mode + 3 keys). Pack covers it. |
| 3 | **USB-C *data* cable** | "USB-C data cable short" | ~$6 | ⚠️ Must be **data**, not charge-only — #1 gotcha. |
| 4 | **Breadboard + jumper wires** | "breadboard jumper wire kit" | ~$8 | Prototype before you solder. |

Bare minimum to deploy: **#1 + buttons + data cable**. For a permanent token add perfboard/solder + a mini enclosure ("mini project box 50mm").

---

## Wiring

Internal pull-ups mean each button just shorts a pin to GND — no resistors.

```
        XIAO RP2040 (USB-C at top)
        ┌───────────────┐
        │ D0 │── MODE button ──── GND
        │ D1 │── KEY 1 button ─── GND
        │ D2 │── KEY 2 button ─── GND
        │ D3 │── KEY 3 button ─── GND
        │ GND│── common ground rail
        └───────────────┘

   4-pin tactile switch: use legs diagonal to each other
   (the two legs on one side are shorted internally).
```

---

## Flashing (CircuitPython)

1. **Install CircuitPython** on the XIAO RP2040:
   - Grab the XIAO RP2040 `.uf2` from circuitpython.org/downloads.
   - Hold **B(OOT)**, tap **R(ESET)** (or plug in holding BOOT) → drive `RPI-RP2` appears.
   - Drag the `.uf2` on. It reboots as **CIRCUITPY**.
2. **Add the HID library:** download the CircuitPython **library bundle** (matching your CP major version) from circuitpython.org/libraries and copy the **`adafruit_hid`** folder into `CIRCUITPY/lib/`.
3. **Copy** `boot.py`, `code.py`, `keys.txt` to the root of `CIRCUITPY`.
4. **Edit `keys.txt`** — one credential per line (line 1 = D1, etc.).
5. Eject/replug. It boots in **KEYBOARD** mode — focus a text field and press a key button to confirm. To edit keys later: press **MODE**, the drive remounts, edit `keys.txt`, press **MODE** again.

> `lib/README.txt` just marks where `adafruit_hid` goes — the library itself isn't committed (it's Adafruit's and tracks your CP version).

---

## Security / opsec (lab-honest)

- **`keys.txt` is plaintext.** Hiding the drive in keyboard mode stops casual mounting, but a flash dump reveals everything — a bare RP2040 has **no secure element**. Fine for lab/throwaway creds; **don't** put prod or personal passwords on it.
- **Treat each device as a credential.** Lost board = lost keys. Label them, wipe (`keys.txt` → junk) before they leave your control.
- **Keyboard layout:** `KeyboardLayoutUS` sends **US** scancodes. On a non-US host, symbols come out wrong — keep creds to `[A-Za-z0-9]` or add the matching layout lib.
- **No keystrokes on plug-in** — typing is gated behind the button, so plugging in never fires anything by itself.
- **Auto-Enter:** off by default. Flip `PRESS_ENTER_AFTER_KEY = True` in `code.py` to submit automatically after each key (faster, but mis-fires if focus is wrong).

---

## Files

| File | Role |
|------|------|
| `boot.py` | Chooses USB identity at boot (default KEYBOARD). |
| `code.py` | Main loop: multi-key typing + mode toggle. |
| `keys.txt` | One credential per line. **Edit this.** |
| `lib/README.txt` | Where `adafruit_hid` goes. |

## Sources

- [Seeed XIAO RP2040 (The Pi Hut)](https://thepihut.com/products/seeed-xiao-rp2040) · [ASIN B09NNVNW7M mirror](https://specpicks.com/product/B09NNVNW7M) · [XIAO RP2040 getting started](https://how2electronics.com/getting-started-with-seeed-xiao-rp2040-with-projects/)
- [12mm tactile switch buttons (The Pi Hut)](https://thepihut.com/collections/all/products/tactile-switch-buttons-12mm-square-6mm-tall-x-10-pack) · [200-pc 6mm button kit (ShillehTek)](https://shillehtek.com/products/200pcs-6mm-light-touch-button-switch-kit-plastic-box-4-3-5-6-7-8-9-10-12-14-16mm)
