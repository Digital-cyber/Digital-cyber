"""
boot.py - runs ONCE at power-on / reset, BEFORE USB enumerates.

This is the only place where the device's USB identity can be chosen,
because the host decides what the device "is" (keyboard vs. drive) during
enumeration. We read a single persisted byte from microcontroller NVM to
decide which identity to present this boot.

  NVM byte 0:
      1 = KEYBOARD mode  -> HID keyboard, CIRCUITPY drive hidden
      0 = DRIVE mode     -> plain USB mass-storage, no HID

Live toggle: code.py flips this byte and calls microcontroller.reset(),
which re-runs boot.py and re-enumerates as the other device. NVM is used
(not a file) because in DRIVE mode the host owns the filesystem and the
firmware cannot write to it.

Manual override: hold the MODE button during power-on to flip the stored
mode (useful if you ever get stuck in one identity).

Board: Seeed Studio XIAO RP2040 | CircuitPython 8.x / 9.x
Pins:  MODE button -> D0 -> GND     PASSWORD button -> D1 -> GND
"""

import board
import digitalio
import storage
import usb_hid
import usb_cdc
import microcontroller

MODE_KEYBOARD = 1
MODE_DRIVE = 0

# --- read persisted mode (survives reset/power loss) ---
mode = microcontroller.nvm[0]
if mode not in (MODE_KEYBOARD, MODE_DRIVE):
    mode = MODE_DRIVE  # first-ever boot: behave like a normal, boring USB stick

# --- optional manual override: hold MODE at power-on to flip ---
mode_btn = digitalio.DigitalInOut(board.D0)
mode_btn.switch_to_input(pull=digitalio.Pull.UP)
if not mode_btn.value:            # pressed == pin pulled to GND
    mode ^= 1
    microcontroller.nvm[0] = mode
mode_btn.deinit()

# --- present the chosen USB identity ---
if mode == MODE_KEYBOARD:
    storage.disable_usb_drive()                 # hide CIRCUITPY from the host
    usb_cdc.disable()                           # hide the serial console too (optional)
    usb_hid.enable((usb_hid.Device.KEYBOARD,))  # expose a single HID keyboard
else:
    usb_hid.disable()                           # no HID; just the mass-storage drive
