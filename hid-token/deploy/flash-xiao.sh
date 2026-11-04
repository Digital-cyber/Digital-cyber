#!/usr/bin/env bash
#
# flash-xiao.sh - batch-flash Seeed XIAO RP2040 HID tokens (Linux / macOS).
#
# Loops so you can image a stack of boards one after another. For each board:
#   1. (optional) waits for the RPI-RP2 bootloader volume and writes a
#      CircuitPython .uf2 to it; the board reboots into CircuitPython.
#   2. waits for the CIRCUITPY volume and copies the payload
#      (boot.py, code.py, keys.txt, lib/) onto it.
#   3. tells you it's done; unplug that board and plug in the next.
#
# Put a board in the bootloader first (hold BOOT, tap RESET, or plug in holding
# BOOT) so RPI-RP2 appears. If CircuitPython is already installed, pass
# --skip-firmware and the board shows up as CIRCUITPY directly.
#
# Usage:
#   ./flash-xiao.sh --uf2 ./circuitpython-xiao-rp2040-9.2.1.uf2
#   ./flash-xiao.sh --skip-firmware --keys ./lab-batch-A.txt --count 10
#
# Options:
#   --uf2 <path>       CircuitPython .uf2 (required unless --skip-firmware)
#   --source <dir>     folder with boot.py/code.py/keys.txt/lib (default: parent of this script)
#   --keys <path>      drop this file in as keys.txt (per-batch override)
#   --skip-firmware    board already runs CircuitPython; just push payload
#   --count <n>        number of boards (0/omitted = loop until Ctrl+C)
#   --timeout <sec>    per-drive wait timeout (default 120)

set -u

UF2=""
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE="$(cd "$SCRIPT_DIR/.." && pwd)"
KEYS=""
SKIP_FW=0
COUNT=0
TIMEOUT=120

while [[ $# -gt 0 ]]; do
  case "$1" in
    --uf2) UF2="$2"; shift 2 ;;
    --source) SOURCE="$2"; shift 2 ;;
    --keys) KEYS="$2"; shift 2 ;;
    --skip-firmware) SKIP_FW=1; shift ;;
    --count) COUNT="$2"; shift 2 ;;
    --timeout) TIMEOUT="$2"; shift 2 ;;
    -h|--help) grep '^#' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "Unknown option: $1" >&2; exit 2 ;;
  esac
done

# Candidate mount roots by label, across Linux and macOS.
find_mount() {
  local label="$1" p
  for p in \
    "/Volumes/$label" \
    "/media/$USER/$label" \
    "/run/media/$USER/$label" \
    "/media/$label"; do
    [[ -d "$p" ]] && { echo "$p"; return 0; }
  done
  # Fallback: ask the OS where this label is mounted (Linux).
  if command -v findmnt >/dev/null 2>&1; then
    p="$(findmnt -rno TARGET -S "LABEL=$label" 2>/dev/null | head -n1)"
    [[ -n "$p" && -d "$p" ]] && { echo "$p"; return 0; }
  fi
  return 1
}

wait_mount() {
  local label="$1" deadline=$(( $(date +%s) + TIMEOUT )) m
  while [[ $(date +%s) -lt $deadline ]]; do
    m="$(find_mount "$label")" && { echo "$m"; return 0; }
    sleep 0.5
  done
  return 1
}

wait_gone() {
  local label="$1" deadline=$(( $(date +%s) + 3600 ))
  while [[ $(date +%s) -lt $deadline ]]; do
    find_mount "$label" >/dev/null || return 0
    sleep 0.5
  done
  return 1
}

# --- validate inputs ---
if [[ $SKIP_FW -eq 0 ]]; then
  [[ -n "$UF2" ]] || { echo "ERROR: provide --uf2 <path>, or use --skip-firmware." >&2; exit 2; }
  [[ -f "$UF2" ]] || { echo "ERROR: UF2 not found: $UF2" >&2; exit 2; }
fi
[[ -d "$SOURCE" ]] || { echo "ERROR: source folder not found: $SOURCE" >&2; exit 2; }
for f in boot.py code.py keys.txt; do
  [[ -f "$SOURCE/$f" ]] || { echo "ERROR: missing payload file: $SOURCE/$f" >&2; exit 2; }
done
if [[ ! -d "$SOURCE/lib/adafruit_hid" ]]; then
  echo "WARNING: $SOURCE/lib/adafruit_hid not found - code.py will crash without it." >&2
  echo "         Copy the adafruit_hid folder in (circuitpython.org/libraries)." >&2
fi
[[ -z "$KEYS" || -f "$KEYS" ]] || { echo "ERROR: keys file not found: $KEYS" >&2; exit 2; }

echo "=== XIAO RP2040 batch flasher ==="
echo "Source  : $SOURCE"
if [[ $SKIP_FW -eq 0 ]]; then echo "Firmware: $UF2"; else echo "Firmware: (skipped)"; fi
[[ -n "$KEYS" ]] && echo "Keys    : $KEYS (override)"
if [[ $COUNT -gt 0 ]]; then echo "Boards  : $COUNT"; else echo "Boards  : loop until Ctrl+C"; fi
echo

copy_payload() {
  local dst="$1"
  cp -f "$SOURCE/boot.py" "$SOURCE/code.py" "$dst/"
  if [[ -n "$KEYS" ]]; then cp -f "$KEYS" "$dst/keys.txt"; else cp -f "$SOURCE/keys.txt" "$dst/"; fi
  cp -rf "$SOURCE/lib" "$dst/"
  sync
}

done_count=0
while [[ $COUNT -le 0 || $done_count -lt $COUNT ]]; do
  n=$(( done_count + 1 ))
  echo "--- Board #$n ---"

  if [[ $SKIP_FW -eq 0 ]]; then
    echo "Waiting for RPI-RP2 bootloader (hold BOOT + tap RESET, or plug in holding BOOT)..."
    boot="$(wait_mount RPI-RP2)" || { echo "Timed out waiting for RPI-RP2; retrying."; continue; }
    echo "Writing firmware to $boot ..."
    cp -f "$UF2" "$boot/" 2>/dev/null || true   # drive vanishes as the board reboots
    sync 2>/dev/null || true
    echo "Firmware written; board is rebooting..."
  fi

  echo "Waiting for CIRCUITPY ..."
  cp_mount="$(wait_mount CIRCUITPY)" || { echo "Timed out waiting for CIRCUITPY; retrying."; continue; }

  echo "Copying payload to $cp_mount ..."
  copy_payload "$cp_mount"

  echo "Board #$n done. Safely eject, then unplug."
  done_count=$(( done_count + 1 ))
  [[ $COUNT -gt 0 && $done_count -ge $COUNT ]] && break

  echo "Waiting for you to unplug this board..."
  wait_gone CIRCUITPY
  echo
done

echo
echo "Flashed $done_count board(s)."
