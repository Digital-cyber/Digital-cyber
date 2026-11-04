"""
code.py - main loop. Runs in BOTH modes (HID is simply absent in DRIVE mode).

  PASSWORD button (D1): in KEYBOARD mode, types the secret from /secret.txt.
                        does nothing in DRIVE mode (no HID available).
  MODE button (D0):     flips the persisted mode byte and soft-resets, so the
                        device re-enumerates as the other identity (~1-2s).
                        This is the "live" toggle - works from either mode.

Required library in /lib:  adafruit_hid  (from the CircuitPython library bundle)

Security note: /secret.txt is plaintext. In KEYBOARD mode the drive is hidden
from the host, but anyone who can dump the flash can read it. See README.md.
"""

import time
import board
import digitalio
import microcontroller

MODE_KEYBOARD = 1
MODE_DRIVE = 0

DEBOUNCE_S = 0.03
PRESS_ENTER_AFTER_PASSWORD = False  # set True to hit Enter after typing


def load_secret():
    """Read the secret, stripping trailing newline(s). Empty string on failure."""
    try:
        with open("/secret.txt", "r") as f:
            return f.read().rstrip("\r\n")
    except OSError:
        return ""


# --- buttons (internal pull-ups; pressed = reads False) ---
mode_btn = digitalio.DigitalInOut(board.D0)
mode_btn.switch_to_input(pull=digitalio.Pull.UP)
pass_btn = digitalio.DigitalInOut(board.D1)
pass_btn.switch_to_input(pull=digitalio.Pull.UP)

# --- try to bring up HID; absent in DRIVE mode ---
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
    kbd = None  # DRIVE mode, or HID not ready


def pressed(btn):
    """Debounced edge check."""
    if not btn.value:
        time.sleep(DEBOUNCE_S)
        if not btn.value:
            return True
    return False


def wait_release(btn):
    while not btn.value:
        time.sleep(0.02)


def switch_mode():
    microcontroller.nvm[0] = microcontroller.nvm[0] ^ 1  # flip stored mode
    time.sleep(0.05)
    microcontroller.reset()                              # re-enumerate


while True:
    # Mode toggle works in either identity.
    if pressed(mode_btn):
        wait_release(mode_btn)
        switch_mode()

    # Typing only when HID is live.
    if kbd and pressed(pass_btn):
        secret = load_secret()
        if secret:
            layout.write(secret)
            if PRESS_ENTER_AFTER_PASSWORD:
                kbd.send(Keycode.ENTER)
        wait_release(pass_btn)  # no auto-repeat while held

    time.sleep(0.02)
