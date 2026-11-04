"""
boot.py - runs ONCE at power-on / reset, BEFORE USB enumerates.

USB identity is chosen here (it can only be set at enumeration). A single
persisted NVM byte decides the identity this boot:

  NVM byte 0:
      1 (or unset) = KEYBOARD mode  -> HID keyboard, CIRCUITPY drive hidden
      0            = DRIVE mode      -> plain USB mass-storage, for editing keys

RAPID-DEPLOY DEFAULT: a freshly flashed board boots straight into KEYBOARD
mode, so it's "keys in hand" the moment it's plugged in. You only drop to
DRIVE mode (MODE button) when you want to edit keys.txt.

Manual override: hold the MODE button during power-on to flip the stored mode
(handy if you ever get stuck in one identity).

Board: Seeed Studio XIAO RP2040 | CircuitPython 8.x / 9.x
Pins:  MODE -> D0   KEY1 -> D1   KEY2 -> D2   KEY3 -> D3   (all to GND)
"""

import board
import digitalio
import storage
import usb_hid
import usb_cdc
import microcontroller

MODE_KEYBOARD = 1
MODE_DRIVE = 0

# --- read persisted mode; default to KEYBOARD for rapid deploy ---
mode = microcontroller.nvm[0]
if mode not in (MODE_KEYBOARD, MODE_DRIVE):
    mode = MODE_KEYBOARD  # first-ever boot: ready to type immediately

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
    usb_hid.disable()                           # no HID; just the editable drive
