"""
code.py - main loop. Quick-and-dirty multi-key typer for lab deployment.

  KEY buttons (D1, D2, D3): each types the matching line from /keys.txt
                            (D1 -> line 1, D2 -> line 2, D3 -> line 3).
                            Only active in KEYBOARD mode.
  MODE button (D0):         flips identity (KEYBOARD <-> DRIVE) and soft-resets
                            so you can mount the drive and edit keys.txt.

Add more keys: wire another button and append its pin to KEY_PINS below;
it maps to the next line of keys.txt automatically.

Required library in /lib:  adafruit_hid  (CircuitPython library bundle)

Security note: /keys.txt is plaintext (no secure element on a bare RP2040).
Fine for lab creds; don't put anything you'd cry over on it. See README.md.
"""

import time
import board
import digitalio
import microcontroller

MODE_KEYBOARD = 1
MODE_DRIVE = 0

DEBOUNCE_S = 0.03
PRESS_ENTER_AFTER_KEY = False   # set True to auto-submit after typing each key

# Buttons that fire keys, in order. KEY_PINS[i] -> keys.txt line (i+1).
KEY_PIN_NAMES = ("D1", "D2", "D3")


def load_keys():
    """Return keys.txt as a list of lines (newline-stripped). [] on failure."""
    try:
        with open("/keys.txt", "r") as f:
            return [ln.rstrip("\r\n") for ln in f.readlines()]
    except OSError:
        return []


# --- MODE button ---
mode_btn = digitalio.DigitalInOut(board.D0)
mode_btn.switch_to_input(pull=digitalio.Pull.UP)

# --- KEY buttons ---
key_btns = []
for name in KEY_PIN_NAMES:
    pin = getattr(board, name, None)
    if pin is None:
        continue
    b = digitalio.DigitalInOut(pin)
    b.switch_to_input(pull=digitalio.Pull.UP)
    key_btns.append(b)

# --- bring up HID (absent in DRIVE mode) ---
kbd = None
layout = None
try:
    import usb_hid
    from adafruit_hid.keyboard import Keyboard
    from adafruit_hid.keycode import Keycode
    from adafruit_hid.keyboard_layout_us import KeyboardLayoutUS

    if usb_hid.devices:
        kbd = Keyboard(usb_hid.devices)
        layout = KeyboardLayoutUS(kbd)
except Exception:
    kbd = None


def pressed(btn):
    if not btn.value:
        time.sleep(DEBOUNCE_S)
        if not btn.value:
            return True
    return False


def wait_release(btn):
    while not btn.value:
        time.sleep(0.02)


def switch_mode():
    microcontroller.nvm[0] = microcontroller.nvm[0] ^ 1
    time.sleep(0.05)
    microcontroller.reset()


while True:
    # Drop to / return from editable drive.
    if pressed(mode_btn):
        wait_release(mode_btn)
        switch_mode()

    # Fire a key.
    if kbd:
        for i, b in enumerate(key_btns):
            if pressed(b):
                keys = load_keys()
                if i < len(keys) and keys[i]:
                    layout.write(keys[i])
                    if PRESS_ENTER_AFTER_KEY:
                        kbd.send(Keycode.ENTER)
                wait_release(b)

    time.sleep(0.02)
