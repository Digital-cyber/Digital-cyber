#!/usr/bin/env python3
"""
flash-xiao.py - portable batch flasher for Seeed XIAO RP2040 HID tokens.

Stdlib only (no pip installs). Works on Windows, Linux and macOS.

Loops so you can image a stack of boards one after another. For each board:
  1. (optional) waits for the RPI-RP2 bootloader drive and writes a
     CircuitPython .uf2 to it; the board reboots into CircuitPython.
  2. waits for the CIRCUITPY drive and copies the payload
     (boot.py, code.py, keys.txt, lib/) onto it.
  3. tells you it's done; unplug that board and plug in the next.

Put a board into the bootloader first (hold B(OOT), tap R(ESET), or plug in
holding BOOT) so RPI-RP2 appears. If CircuitPython is already installed, pass
--skip-firmware and the board shows up as CIRCUITPY directly.

Examples:
  python3 flash-xiao.py --uf2 ./circuitpython-xiao-rp2040-9.2.1.uf2
  python3 flash-xiao.py --skip-firmware --keys ./lab-batch-A.txt --count 10
"""
import argparse
import getpass
import os
import platform
import shutil
import subprocess
import sys
import time

PAYLOAD_FILES = ("boot.py", "code.py", "keys.txt")


# ---------- drive detection (by volume label) ----------
def _find_mount_windows(label):
    import ctypes
    import string

    k32 = ctypes.windll.kernel32
    k32.SetErrorMode(0x0001)  # SEM_FAILCRITICALERRORS: no "insert disk" popups
    bitmask = k32.GetLogicalDrives()
    for i, letter in enumerate(string.ascii_uppercase):
        if not (bitmask >> i) & 1:
            continue
        root = f"{letter}:\\"
        vol = ctypes.create_unicode_buffer(261)
        fsname = ctypes.create_unicode_buffer(261)
        serial = ctypes.c_uint32()
        maxcomp = ctypes.c_uint32()
        flags = ctypes.c_uint32()
        ok = k32.GetVolumeInformationW(
            ctypes.c_wchar_p(root),
            vol, len(vol),
            ctypes.byref(serial), ctypes.byref(maxcomp), ctypes.byref(flags),
            fsname, len(fsname),
        )
        if ok and vol.value == label:
            return root
    return None


def find_mount(label):
    if platform.system() == "Windows":
        return _find_mount_windows(label)

    user = getpass.getuser()
    for cand in (
        f"/Volumes/{label}",            # macOS
        f"/run/media/{user}/{label}",   # Linux (udisks2)
        f"/media/{user}/{label}",       # Linux (older)
        f"/media/{label}",
    ):
        if os.path.isdir(cand):
            return cand

    # Linux fallback: ask the OS where this label is mounted.
    try:
        out = subprocess.run(
            ["findmnt", "-rno", "TARGET", "-S", f"LABEL={label}"],
            capture_output=True, text=True, check=False,
        )
        lines = out.stdout.strip().splitlines()
        if lines and os.path.isdir(lines[0]):
            return lines[0]
    except (FileNotFoundError, OSError):
        pass
    return None


def wait_mount(label, timeout):
    deadline = time.time() + timeout
    while time.time() < deadline:
        m = find_mount(label)
        if m:
            return m
        time.sleep(0.5)
    return None


def wait_gone(label, timeout=3600):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if not find_mount(label):
            return True
        time.sleep(0.5)
    return False


# ---------- payload copy ----------
def copy_payload(source, dst, keys_file):
    shutil.copy2(os.path.join(source, "boot.py"), dst)
    shutil.copy2(os.path.join(source, "code.py"), dst)
    if keys_file:
        shutil.copy2(keys_file, os.path.join(dst, "keys.txt"))
    else:
        shutil.copy2(os.path.join(source, "keys.txt"), dst)
    shutil.copytree(os.path.join(source, "lib"),
                    os.path.join(dst, "lib"), dirs_exist_ok=True)
    try:
        if hasattr(os, "sync"):
            os.sync()
    except OSError:
        pass


# ---------- main ----------
def main(argv=None):
    here = os.path.dirname(os.path.abspath(__file__))
    default_source = os.path.dirname(here)  # the hid-token folder

    ap = argparse.ArgumentParser(description="Batch-flash XIAO RP2040 HID tokens.")
    ap.add_argument("--uf2", help="CircuitPython .uf2 (required unless --skip-firmware)")
    ap.add_argument("--source", default=default_source,
                    help="folder with boot.py/code.py/keys.txt/lib (default: parent of this script)")
    ap.add_argument("--keys", help="drop this file in as keys.txt (per-batch override)")
    ap.add_argument("--skip-firmware", action="store_true",
                    help="board already runs CircuitPython; just push payload")
    ap.add_argument("--count", type=int, default=0,
                    help="number of boards (0 = loop until Ctrl+C)")
    ap.add_argument("--timeout", type=int, default=120,
                    help="per-drive wait in seconds (default 120)")
    args = ap.parse_args(argv)

    # validate
    if not args.skip_firmware:
        if not args.uf2:
            ap.error("provide --uf2 <path>, or use --skip-firmware")
        if not os.path.isfile(args.uf2):
            ap.error(f"UF2 not found: {args.uf2}")
    if not os.path.isdir(args.source):
        ap.error(f"source folder not found: {args.source}")
    for f in PAYLOAD_FILES:
        if not os.path.isfile(os.path.join(args.source, f)):
            ap.error(f"missing payload file: {os.path.join(args.source, f)}")
    if not os.path.isdir(os.path.join(args.source, "lib", "adafruit_hid")):
        print("WARNING: lib/adafruit_hid not found under "
              f"{os.path.join(args.source, 'lib')} - code.py will crash without it.",
              file=sys.stderr)
        print("         Copy the adafruit_hid folder in (circuitpython.org/libraries).",
              file=sys.stderr)
    if args.keys and not os.path.isfile(args.keys):
        ap.error(f"keys file not found: {args.keys}")

    print("=== XIAO RP2040 batch flasher (python) ===")
    print(f"Source  : {args.source}")
    print(f"Firmware: {args.uf2 if not args.skip_firmware else '(skipped)'}")
    if args.keys:
        print(f"Keys    : {args.keys} (override)")
    print(f"Boards  : {args.count if args.count > 0 else 'loop until Ctrl+C'}\n")

    done = 0
    try:
        while args.count <= 0 or done < args.count:
            n = done + 1
            print(f"--- Board #{n} ---")

            if not args.skip_firmware:
                print("Waiting for RPI-RP2 bootloader (hold BOOT + tap RESET, or plug in holding BOOT)...")
                boot = wait_mount("RPI-RP2", args.timeout)
                if not boot:
                    print("Timed out waiting for RPI-RP2; retrying.")
                    continue
                print(f"Writing firmware to {boot} ...")
                try:
                    shutil.copy2(args.uf2, boot)
                except OSError:
                    pass  # board reboots mid-copy; drive vanishes
                print("Firmware written; board is rebooting...")

            print("Waiting for CIRCUITPY ...")
            cp = wait_mount("CIRCUITPY", args.timeout)
            if not cp:
                print("Timed out waiting for CIRCUITPY; retrying.")
                continue

            print(f"Copying payload to {cp} ...")
            copy_payload(args.source, cp, args.keys)
            print(f"Board #{n} done. Safely eject, then unplug.")
            done += 1

            if args.count > 0 and done >= args.count:
                break
            print("Waiting for you to unplug this board...")
            wait_gone("CIRCUITPY")
            print()
    except KeyboardInterrupt:
        print()

    print(f"\nFlashed {done} board(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
