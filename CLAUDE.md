# CLAUDE.md — Digital-cyber Repository

## Repository Overview

This is a cybersecurity and systems administration portfolio by Wayne Bianchetta. It contains standalone PowerShell scripts and a Python honeypot for Windows environments, Active Directory administration, and defensive security monitoring. There is no build system, package manager, or test framework — each file is a self-contained, runnable script.

## Repository Structure

```
Digital-cyber/
├── SecurityLogExporter.ps1   # Failed RDP login monitor with geolocation enrichment
├── JWipe.ps1                 # Interactive disk sanitization utility
├── FileIntegrity.ps1         # File Integrity Monitor (FIM) using SHA-512 hashing
├── CreateUsers.ps1           # Bulk AD user creation from a names.txt file
├── NameGenerator.ps1         # Random-name AD user bulk creation (lab environments)
├── honeypot.py               # TCP honeypot listening on port 80
└── README.md                 # GitHub profile README with project links
```

## Script Summaries

### SecurityLogExporter.ps1
- Polls Windows Event Viewer indefinitely for Event ID 4625 (failed RDP logons).
- Enriches each event with geolocation data (latitude, longitude, country, state) via the [ipgeolocation.io](https://ipgeolocation.io/) API.
- Writes enriched records to `C:\ProgramData\failed_rdp.log` in a pipe-delimited format compatible with Azure Log Analytics / Microsoft Sentinel custom log ingestion.
- Contains sample log entries (destinationhost: `samplehost`) used to train the Log Analytics Extract feature — filter these out when building KQL queries.
- **Requires:** Windows, PowerShell, an `ipgeolocation.io` API key (set `$API_KEY`).

### JWipe.ps1
- Interactive CLI disk wipe utility using `diskpart.exe`.
- Lists attached disks, prompts for the target disk ID, number of passes (1–99), and a typed `confirm` before wiping.
- Safety guard: exits if fewer than 2 disks are attached to avoid accidentally wiping a USB boot drive.
- Each pass issues `clean all` (zero-fills the disk) via a generated `unattend.txt` diskpart script.
- **Requires:** Windows, PowerShell, Administrator privileges, `diskpart.exe`.

### FileIntegrity.ps1
- Two-mode FIM: `A` collects a fresh SHA-512 baseline from `.\Files\`; `B` monitors continuously against that baseline.
- Baseline stored in `.\baseline.txt` as `<path>|<hash>` pairs.
- Monitoring detects and reports: new files (green), modified files (yellow), deleted files (dark red).
- Polling interval: 1 second.
- **Requires:** Windows, PowerShell. A `.\Files\` directory must exist.

### CreateUsers.ps1
- Reads `.\names.txt` (one `Firstname Lastname` per line).
- Creates an `_USERS` OU in the current domain root and bulk-creates AD users with username format `flastname`.
- Password set from `$PASSWORD_FOR_USERS` (default: `Password1`); passwords never expire.
- **Requires:** Windows, PowerShell, Active Directory module (`RSAT`), domain-joined machine, Domain Admin privileges.

### NameGenerator.ps1
- Generates up to 10,000 random phonetic usernames (consonant-vowel alternation, 3–6 chars each part).
- Creates AD users in `ou=_EMPLOYEES` OU with `$PASSWORD_FOR_USERS` (default: `Password1`).
- Intended for lab/homelab environments to populate AD for testing.
- **Requires:** Same as CreateUsers.ps1.

### honeypot.py
- Minimal TCP server on `0.0.0.0:80` (all interfaces, HTTP port).
- Accepts connections, sends an empty `HTTP/1.1 200 OK` response, and logs the source IP/port to stdout.
- Uses Python's `threading` module to handle multiple simultaneous connections.
- **Requires:** Python 3, root/admin privileges (port 80), Linux/Windows.

## Development Conventions

### PowerShell Style
- PascalCase for function names using hyphenated verbs: `gather-Input-From-User`, `Calculate-File-Hash`.
- Global variables declared at the top with `$global:` prefix when shared across functions.
- User-configurable variables are grouped at the top of each script under a clearly marked comment block:
  ```powershell
  # ----- Edit these Variables for your own Use Case ----- #
  $VARIABLE = "value"
  # ------------------------------------------------------ #
  ```
- `Write-Host` is used for all console output; color coding convention:
  - Cyan = informational progress
  - Green = success / new file created
  - Yellow = warning / file changed
  - Red = critical info / disk IDs
  - DarkRed on Gray = deletion alert
  - Magenta = log export output

### Python Style
- Standard library only (no third-party dependencies).
- Module-level constants in `ALL_CAPS`.
- Single-file scripts with a simple top-to-bottom execution flow plus threading for concurrency.

### No Build / No Tests
- There is no CI pipeline, linter config, test suite, or package manifest in this repository.
- Scripts are validated by running them directly in their target environment.
- Do not introduce package managers, test frameworks, or build tooling unless explicitly requested.

## Key Conventions for AI Assistants

1. **Do not add complexity.** These are intentionally simple, self-contained scripts. Avoid refactoring into modules, classes, or helper libraries unless explicitly asked.
2. **Preserve the user-configurable variable block** at the top of PowerShell scripts — this is the intended customization interface.
3. **Credentials and API keys are hardcoded** (e.g., `$API_KEY`, `$PASSWORD_FOR_USERS`). Do not move them without being asked, but do flag them as security-sensitive if relevant.
4. **Windows-only assumptions.** PowerShell scripts assume Windows AD, `diskpart.exe`, and Windows Event Viewer APIs. Do not introduce cross-platform abstractions.
5. **The honeypot is defensive/educational.** It logs inbound connections and sends a benign response. Do not extend it with offensive capabilities.
6. **README.md is a GitHub profile README** (HTML-formatted). Edits should preserve the HTML structure.

## Environment Requirements

| Script                  | OS      | Privileges     | External Dependencies            |
|-------------------------|---------|----------------|----------------------------------|
| SecurityLogExporter.ps1 | Windows | Standard       | ipgeolocation.io API key         |
| JWipe.ps1               | Windows | Administrator  | diskpart.exe                     |
| FileIntegrity.ps1       | Windows | Standard       | `.\Files\` directory             |
| CreateUsers.ps1         | Windows | Domain Admin   | AD RSAT module, `.\names.txt`    |
| NameGenerator.ps1       | Windows | Domain Admin   | AD RSAT module                   |
| honeypot.py             | Any     | Root/Admin     | Python 3 standard library        |

## Git Workflow

- Default branch: `main`
- No enforced commit message format; use clear, descriptive messages.
- No pre-commit hooks are active (only `.sample` hooks exist).
- Development branches follow the pattern: `claude/<description>-<sessionId>`
