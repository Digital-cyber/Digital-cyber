# deploy — batch-flash a stack of XIAO RP2040 tokens

Image many boards back-to-back. The script loops: flash one → unplug → plug next → repeat.

- **Windows / PowerShell:** `flash-xiao.ps1` (primary)
- **Linux / macOS:** `flash-xiao.sh`

Both do the same two steps per board and default their payload source to the parent `hid-token/` folder (`boot.py`, `code.py`, `keys.txt`, `lib/`).

```
   per board:
   ┌──────────────────────────────────────────────┐
   │ 1. board in BOOTLOADER  → RPI-RP2 mounts       │
   │      └─ copy CircuitPython .uf2  → reboots      │
   │ 2. board as CIRCUITPY   → copy payload:         │
   │      boot.py  code.py  keys.txt  lib\adafruit_hid│
   │ 3. "done" → unplug → next board                 │
   └──────────────────────────────────────────────┘
```

## One-time prep

1. Download the XIAO RP2040 **CircuitPython `.uf2`** (circuitpython.org/downloads).
2. Download the **library bundle** (circuitpython.org/libraries) and copy its `adafruit_hid` folder into `hid-token/lib/`. The scripts warn loudly if it's missing — without it `code.py` crashes.
3. Edit `hid-token/keys.txt` (or keep a per-batch file and pass `-KeysFile` / `--keys`).

## Put a board in the bootloader

Hold **B(OOT)**, tap **R(ESET)** (or plug in while holding BOOT). The `RPI-RP2` drive appears. Skip this with `-SkipFirmware` / `--skip-firmware` if CircuitPython is already installed (board shows as `CIRCUITPY`).

## Run it

**Windows:**
```powershell
# Flash firmware + payload, loop until Ctrl+C
.\flash-xiao.ps1 -Uf2 .\adafruit-circuitpython-seeeduino_xiao_rp2040-9.2.1.uf2

# 10 boards, firmware already present, batch-specific keys
.\flash-xiao.ps1 -SkipFirmware -KeysFile .\lab-batch-A.txt -Count 10
```
> If scripts are blocked: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` for the current window only.

**Linux / macOS:**
```bash
./flash-xiao.sh --uf2 ./circuitpython-xiao-rp2040-9.2.1.uf2
./flash-xiao.sh --skip-firmware --keys ./lab-batch-A.txt --count 10
```

## Options

| PowerShell | bash | Meaning |
|---|---|---|
| `-Uf2 <path>` | `--uf2 <path>` | CircuitPython .uf2 (required unless skipping firmware) |
| `-Source <dir>` | `--source <dir>` | Payload folder (default: parent `hid-token/`) |
| `-KeysFile <path>` | `--keys <path>` | Drop this in as `keys.txt` for the batch |
| `-SkipFirmware` | `--skip-firmware` | Board already runs CircuitPython |
| `-Count <n>` | `--count <n>` | Number of boards (0 = loop until Ctrl+C) |
| `-TimeoutSec <s>` | `--timeout <s>` | Per-drive wait (default 120s) |

## Notes & gotchas

- **Drive detection is by volume label** (`RPI-RP2`, `CIRCUITPY`). If you've renamed `CIRCUITPY`, the scripts won't find it — keep the default label.
- **One board at a time.** Detection is label-based; two `CIRCUITPY` drives at once are ambiguous. Plug the next only after "done."
- **Eject before yanking.** The scripts `sync` (bash) / copy synchronously (PowerShell), but still eject to be safe, especially on Windows where writes can be cached.
- **Firmware copy "errors" are normal** — the board reboots mid-write and the drive disappears; both scripts swallow that.
- **`keys.txt` is plaintext** on every board you image. Same lab-opsec caveats as the main README: throwaway/lab creds only, treat each board as a credential.

*Confidence:* label-based mount detection covers the standard Windows, GNOME/udisks (`/run/media` or `/media`), and macOS (`/Volumes`) paths, with a `findmnt` fallback on Linux. On a headless Linux box with no auto-mounter you'll need to mount manually (or tell me and I'll add an auto-mount path). PowerShell couldn't be executed in my build environment, so I authored it against documented `Get-Volume`/`Copy-Item` behavior — if anything misfires on your box, paste the error and I'll fix it fast.
