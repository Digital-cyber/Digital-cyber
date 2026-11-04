<#
.SYNOPSIS
    Batch-flash Seeed XIAO RP2040 HID tokens (Windows / PowerShell).

.DESCRIPTION
    Loops so you can image a stack of boards one after another. For each board:
      1. (optional) waits for the RPI-RP2 bootloader drive and writes a
         CircuitPython .uf2 to it. The board reboots into CircuitPython.
      2. waits for the CIRCUITPY drive and copies the token payload
         (boot.py, code.py, keys.txt, lib\) onto it.
      3. tells you it's done; unplug that board and plug in the next.

    Put a board into the bootloader first (hold B(OOT), tap R(ESET), or plug in
    while holding BOOT) so RPI-RP2 appears. If CircuitPython is already
    installed, use -SkipFirmware and the board shows up as CIRCUITPY directly.

.PARAMETER Uf2
    Path to the CircuitPython .uf2 for the XIAO RP2040. Required unless -SkipFirmware.

.PARAMETER Source
    Folder containing boot.py, code.py, keys.txt and lib\. Defaults to the
    parent of this script (the hid-token folder).

.PARAMETER KeysFile
    Optional path to a keys file to drop in as keys.txt (per-batch override).

.PARAMETER SkipFirmware
    Board already runs CircuitPython; skip the .uf2 step, just push the payload.

.PARAMETER Count
    How many boards to flash. 0 (default) = loop until you press Ctrl+C.

.PARAMETER TimeoutSec
    How long to wait for each drive to appear (default 120s).

.EXAMPLE
    .\flash-xiao.ps1 -Uf2 .\adafruit-circuitpython-seeeduino_xiao_rp2040-9.2.1.uf2

.EXAMPLE
    .\flash-xiao.ps1 -SkipFirmware -KeysFile .\lab-batch-A.txt -Count 10
#>
[CmdletBinding()]
param(
    [string]$Uf2,
    [string]$Source = (Split-Path -Parent $PSScriptRoot),
    [string]$KeysFile,
    [switch]$SkipFirmware,
    [int]$Count = 0,
    [int]$TimeoutSec = 120
)

$ErrorActionPreference = 'Stop'

function Get-DriveRoot([string]$Label) {
    $v = Get-Volume -FileSystemLabel $Label -ErrorAction SilentlyContinue |
         Where-Object { $_.DriveLetter } | Select-Object -First 1
    if ($v) { return "$($v.DriveLetter):\" }
    return $null
}

function Wait-DriveRoot([string]$Label, [int]$Timeout) {
    $deadline = (Get-Date).AddSeconds($Timeout)
    while ((Get-Date) -lt $deadline) {
        $root = Get-DriveRoot $Label
        if ($root -and (Test-Path $root)) { return $root }
        Start-Sleep -Milliseconds 500
    }
    return $null
}

function Wait-DriveGone([string]$Label, [int]$Timeout) {
    $deadline = (Get-Date).AddSeconds($Timeout)
    while ((Get-Date) -lt $deadline) {
        if (-not (Get-DriveRoot $Label)) { return $true }
        Start-Sleep -Milliseconds 500
    }
    return $false
}

# --- validate inputs up front ---
if (-not $SkipFirmware) {
    if (-not $Uf2) { throw "Provide -Uf2 <path to CircuitPython .uf2>, or use -SkipFirmware." }
    if (-not (Test-Path -LiteralPath $Uf2)) { throw "UF2 not found: $Uf2" }
}
if (-not (Test-Path -LiteralPath $Source)) { throw "Source folder not found: $Source" }

$payloadFiles = @('boot.py', 'code.py', 'keys.txt')
foreach ($f in $payloadFiles) {
    if (-not (Test-Path -LiteralPath (Join-Path $Source $f))) {
        throw "Missing payload file: $(Join-Path $Source $f)"
    }
}
$libSrc = Join-Path $Source 'lib'
if (-not (Test-Path -LiteralPath (Join-Path $libSrc 'adafruit_hid'))) {
    Write-Warning "lib\adafruit_hid not found under $libSrc."
    Write-Warning "code.py will crash without it. Copy the adafruit_hid folder into $libSrc first."
    Write-Warning "(Download the CircuitPython library bundle from circuitpython.org/libraries.)"
}
if ($KeysFile -and -not (Test-Path -LiteralPath $KeysFile)) { throw "KeysFile not found: $KeysFile" }

Write-Host "=== XIAO RP2040 batch flasher ===" -ForegroundColor Cyan
Write-Host "Source  : $Source"
if (-not $SkipFirmware) { Write-Host "Firmware: $Uf2" } else { Write-Host "Firmware: (skipped)" }
if ($KeysFile) { Write-Host "Keys    : $KeysFile (override)" }
Write-Host ("Boards  : {0}" -f ($(if ($Count -gt 0) { $Count } else { 'loop until Ctrl+C' })))
Write-Host ""

$done = 0
try {
    while ($Count -le 0 -or $done -lt $Count) {
        $n = $done + 1
        Write-Host "--- Board #$n ---" -ForegroundColor Yellow

        if (-not $SkipFirmware) {
            Write-Host "Waiting for RPI-RP2 bootloader (hold BOOT + tap RESET, or plug in holding BOOT)..."
            $boot = Wait-DriveRoot 'RPI-RP2' $TimeoutSec
            if (-not $boot) { Write-Warning "Timed out waiting for RPI-RP2. Retrying this board."; continue }

            Write-Host "Writing firmware to $boot ..."
            try {
                Copy-Item -LiteralPath $Uf2 -Destination $boot -Force
            } catch {
                # Expected: the board reboots mid-copy and the drive vanishes.
                Write-Verbose "Copy returned (drive likely rebooted): $($_.Exception.Message)"
            }
            Write-Host "Firmware written; board is rebooting..."
        }

        Write-Host "Waiting for CIRCUITPY ..."
        $cp = Wait-DriveRoot 'CIRCUITPY' $TimeoutSec
        if (-not $cp) { Write-Warning "Timed out waiting for CIRCUITPY. Retrying this board."; continue }

        Write-Host "Copying payload to $cp ..."
        foreach ($f in $payloadFiles) {
            Copy-Item -LiteralPath (Join-Path $Source $f) -Destination $cp -Force
        }
        if ($KeysFile) {
            Copy-Item -LiteralPath $KeysFile -Destination (Join-Path $cp 'keys.txt') -Force
        }
        Copy-Item -LiteralPath $libSrc -Destination $cp -Recurse -Force

        Write-Host "Board #$n done. Safely eject, then unplug." -ForegroundColor Green
        $done++

        if ($Count -gt 0 -and $done -ge $Count) { break }

        Write-Host "Waiting for you to unplug this board..."
        [void](Wait-DriveGone 'CIRCUITPY' 3600)
        Write-Host ""
    }
}
catch [System.Management.Automation.PipelineStoppedException] {
    # Ctrl+C
}

Write-Host ""
Write-Host "Flashed $done board(s)." -ForegroundColor Cyan
