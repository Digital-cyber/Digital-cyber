# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Purpose

Cybersecurity and sysadmin portfolio by Wayne Bianchetta. All scripts are standalone — no build system, package manager, test framework, or CI pipeline exists. Each file runs independently in its target environment.

## Running Scripts

**PowerShell scripts** (Windows only, some require elevated privileges):
```powershell
# Run any script directly
.\SecurityLogExporter.ps1
.\JWipe.ps1
.\FileIntegrity.ps1
.\CreateUsers.ps1
.\NameGenerator.ps1

# If execution policy blocks running:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**Python honeypot** (requires root/admin for port 80):
```bash
# Linux
sudo python3 honeypot.py

# Windows (elevated prompt)
python honeypot.py
```

## Script Architecture

All scripts are single-file with no imports beyond standard libraries/modules.

**SecurityLogExporter.ps1** — Infinite loop polling Windows Event Viewer for Event ID 4625 (failed RDP). Enriches each event with geolocation via `ipgeolocation.io` API, deduplicates by timestamp, and appends to `C:\ProgramData\failed_rdp.log`. The log format is a custom pipe/comma-delimited string designed for Azure Log Analytics / Microsoft Sentinel ingestion. Sample records (destinationhost=`samplehost`) are written on first run to satisfy the Log Analytics Extract training requirement — filter them with `| where DestinationHost != "samplehost"` in KQL.

**FileIntegrity.ps1** — Two-phase: mode A hashes all files in `.\Files\` with SHA-512 and writes `path|hash` pairs to `.\baseline.txt`; mode B loads that baseline into a hashtable and polls every second, reporting new/changed/deleted files by color-coded `Write-Host`.

**JWipe.ps1** — Wraps `diskpart.exe` to zero-fill a user-selected disk N times. Generates a temporary `unattend.txt` diskpart script per pass, then a final `clean all` pass. Guards against single-disk systems to prevent wiping the boot USB.

**CreateUsers.ps1 / NameGenerator.ps1** — Both create AD users via `New-AdUser` in a target OU. `CreateUsers.ps1` reads `.\names.txt` (one `Firstname Lastname` per line) and derives username as `flastname`. `NameGenerator.ps1` generates phonetic random names (consonant-vowel alternation) and targets `ou=_EMPLOYEES`.

**honeypot.py** — Binds TCP on `0.0.0.0:80`, accepts connections in a `while True` loop, spawns a thread per client via `threading.Thread`, sends an empty HTTP 200, and prints the source address.

## Conventions

- User-configurable values are always at the top of each PowerShell script in a clearly marked block — this is the intended customization interface, not function parameters.
- `Write-Host` color scheme across all PS scripts: Cyan = progress, Green = created, Yellow = changed/warning, Red = critical, DarkRed on Gray = deleted.
- No cross-platform abstractions — PowerShell scripts depend on Windows AD (`New-AdUser`), `diskpart.exe`, and `Get-WinEvent`.
