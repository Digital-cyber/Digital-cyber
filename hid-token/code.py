"""
code.py - main loop. Quick-and-dirty multi-key typer for lab deployment,
with a mode-indicator LED.

  KEY buttons (D1, D2, D3): each types the matching line from /keys.txt
                            (D1 -> line 1, D2 -> line 2, D3 -> line 3).
                            Only active in KEYBOARD mode.
  MODE button (D0):         flips identity (KEYBOARD <-> DRIVE) and soft-resets
                            so you can mount the drive and edit keys.txt.
  STATUS LED:               solid  = KEYBOARD mode (ready to type)
                            blink  = DRIVE mode (editable USB stick)
                            Driven on an external pin (D6) for an enclosed
                            build, AND on the onboard LEDs for bench use.

Add more keys: wire another button and append its pin to KEY_PIN_NAMES below;
it maps to the next line of keys.txt automatically.

Required library in /lib:  adafruit_hid  (CircuitPython library bundle)
No extra library needed for the LED (plain digitalio).

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
BLINK_PERIOD_S = 0.4            # drive-mode blink half-period
PRESS_ENTER_AFTER_KEY = False  # set True to auto-submit after typing each key

# Buttons that fire keys, in order. KEY_PIN_NAMES[i] -> keys.txt line (i+1).
KEY_PIN_NAMES = ("D1", "D2", "D3")

# External status LED (for an enclosed build): pin -> 330R -> LED -> GND.
STATUS_LED_PIN = "D6"


def load_keys():
    """Return keys.txt as a list of lines (newline-stripped). [] on failure."""
    try:
        with open("/keys.txt", "r") as f:
            return [ln.rstrip("\r\n") for ln in f.readlines()]
    except OSError:
        return []


# ---------- buttons ----------
mode_btn = digitalio.DigitalInOut(board.D0)
mode_btn.switch_to_input(pull=digitalio.Pull.UP)

key_btns = []
for name in KEY_PIN_NAMES:
    pin = getattr(board, name, None)
    if pin is None:
        continue
    b = digitalio.DigitalInOut(pin)
    b.switch_to_input(pull=digitalio.Pull.UP)
    key_btns.append(b)


# ---------- status LEDs ----------
def _make_output(name, start_on, active_low):
    """Create an output pin if it exists; return (io, active_low) or None."""
    pin = getattr(board, name, None)
    if pin is None:
        return None
    try:
        io = digitalio.DigitalInOut(pin)
        # active_low: value True == OFF, so initialize accordingly
        io.switch_to_output(value=(not start_on) if active_low else start_on)
        return (io, active_low)
    except Exception:
        return None


# External LED on a free GPIO (active-high). Onboard RGB LEDs are active-low.
ext_led = _make_output(STATUS_LED_PIN, start_on=False, active_low=False)
onboard_kbd = _make_output("LED_GREEN", start_on=False, active_low=True)  # solid in keyboard mode
onboard_drv = _make_output("LED_BLUE", start_on=False, active_low=True)   # blink in drive mode


def _set(led, on):
    if led is None:
        return
    io, active_low = led
    io.value = (not on) if active_low else on


def update_leds(in_keyboard):
    """Solid when in keyboard mode; blink when in drive mode."""
    if in_keyboard:
        blink_on = True
    else:
        blink_on = int(time.monotonic() / BLINK_PERIOD_S) % 2 == 0
    _set(ext_led, blink_on)                       # external: tells the whole story
    _set(onboard_kbd, in_keyboard)                # green solid = keyboard
    _set(onboard_drv, (not in_keyboard) and blink_on)  # blue blink = drive


# ---------- HID (absent in DRIVE mode) ----------
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

in_keyboard = kbd is not None


def pressed(btn):
    if not btn.value:
        time.sleep(DEBOUNCE_S)
        if not btn.value:
            return True
    return False


def wait_release(btn):
    while not btn.value:
        update_leds(in_keyboard)   # keep the blink alive while held
        time.sleep(0.02)


def switch_mode():
    microcontroller.nvm[0] = microcontroller.nvm[0] ^ 1
    time.sleep(0.05)
    microcontroller.reset()


while True:
    update_leds(in_keyboard)

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
