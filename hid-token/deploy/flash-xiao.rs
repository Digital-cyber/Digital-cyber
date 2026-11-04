//! flash-xiao.rs - portable batch flasher for Seeed XIAO RP2040 HID tokens.
//!
//! std only, no external crates. Build with plain rustc:
//!     rustc -O flash-xiao.rs -o flash-xiao          (Linux/macOS)
//!     rustc -O flash-xiao.rs -o flash-xiao.exe      (Windows)
//!
//! Loops so you can image a stack of boards one after another. For each board:
//!   1. (optional) waits for the RPI-RP2 bootloader volume and writes a
//!      CircuitPython .uf2 to it; the board reboots into CircuitPython.
//!   2. waits for the CIRCUITPY volume and copies the payload
//!      (boot.py, code.py, keys.txt, lib/) onto it.
//!   3. tells you it's done; unplug that board and plug in the next.
//!
//! Examples:
//!   ./flash-xiao --uf2 ./circuitpython-xiao-rp2040-9.2.1.uf2
//!   ./flash-xiao --skip-firmware --keys ./lab-batch-A.txt --count 10
//!
//! Default --source is auto-detected: the first of ".", "..", "../.." that
//! contains boot.py (so run it from deploy/ or hid-token/, or pass --source).

use std::env;
use std::fs;
use std::io;
use std::path::{Path, PathBuf};
use std::thread::sleep;
use std::time::{Duration, Instant};

struct Config {
    uf2: Option<String>,
    source: PathBuf,
    keys: Option<String>,
    skip_fw: bool,
    count: i64,
    timeout: u64,
}

fn usage() -> ! {
    eprintln!(
        "Usage: flash-xiao [--uf2 <path>] [--source <dir>] [--keys <path>]\n\
         \x20              [--skip-firmware] [--count <n>] [--timeout <sec>]\n\n\
         \x20 --uf2 <path>     CircuitPython .uf2 (required unless --skip-firmware)\n\
         \x20 --source <dir>   folder with boot.py/code.py/keys.txt/lib (auto-detected)\n\
         \x20 --keys <path>    drop this file in as keys.txt (per-batch override)\n\
         \x20 --skip-firmware  board already runs CircuitPython; just push payload\n\
         \x20 --count <n>      number of boards (0 = loop until Ctrl+C)\n\
         \x20 --timeout <sec>  per-drive wait (default 120)"
    );
    std::process::exit(2);
}

fn auto_source() -> PathBuf {
    for c in [".", "..", "../.."] {
        let p = PathBuf::from(c);
        if p.join("boot.py").is_file() {
            return p;
        }
    }
    PathBuf::from(".")
}

fn parse_args() -> Config {
    let mut cfg = Config {
        uf2: None,
        source: auto_source(),
        keys: None,
        skip_fw: false,
        count: 0,
        timeout: 120,
    };
    let mut it = env::args().skip(1);
    while let Some(a) = it.next() {
        match a.as_str() {
            "--uf2" => cfg.uf2 = Some(it.next().unwrap_or_else(|| usage())),
            "--source" => cfg.source = PathBuf::from(it.next().unwrap_or_else(|| usage())),
            "--keys" => cfg.keys = Some(it.next().unwrap_or_else(|| usage())),
            "--skip-firmware" => cfg.skip_fw = true,
            "--count" => {
                cfg.count = it.next().and_then(|v| v.parse().ok()).unwrap_or_else(|| usage())
            }
            "--timeout" => {
                cfg.timeout = it.next().and_then(|v| v.parse().ok()).unwrap_or_else(|| usage())
            }
            "-h" | "--help" => usage(),
            other => {
                eprintln!("Unknown option: {other}");
                usage();
            }
        }
    }
    cfg
}

// ---------- drive detection (by volume label) ----------
#[cfg(windows)]
mod platform {
    use std::path::PathBuf;

    #[link(name = "kernel32")]
    extern "system" {
        fn GetLogicalDrives() -> u32;
        fn SetErrorMode(mode: u32) -> u32;
        fn GetVolumeInformationW(
            root: *const u16,
            vol_name: *mut u16,
            vol_size: u32,
            serial: *mut u32,
            max_comp: *mut u32,
            flags: *mut u32,
            fs_name: *mut u16,
            fs_size: u32,
        ) -> i32;
    }

    pub fn find_mount(label: &str) -> Option<PathBuf> {
        unsafe { SetErrorMode(0x0001) }; // SEM_FAILCRITICALERRORS
        let mask = unsafe { GetLogicalDrives() };
        for i in 0..26u32 {
            if (mask >> i) & 1 == 0 {
                continue;
            }
            let letter = (b'A' + i as u8) as char;
            let root: Vec<u16> = format!("{letter}:\\")
                .encode_utf16()
                .chain(std::iter::once(0))
                .collect();
            let mut vol = [0u16; 261];
            let mut fsname = [0u16; 261];
            let (mut serial, mut maxcomp, mut flags) = (0u32, 0u32, 0u32);
            let ok = unsafe {
                GetVolumeInformationW(
                    root.as_ptr(),
                    vol.as_mut_ptr(),
                    vol.len() as u32,
                    &mut serial,
                    &mut maxcomp,
                    &mut flags,
                    fsname.as_mut_ptr(),
                    fsname.len() as u32,
                )
            };
            if ok != 0 {
                let end = vol.iter().position(|&c| c == 0).unwrap_or(vol.len());
                if String::from_utf16_lossy(&vol[..end]) == label {
                    return Some(PathBuf::from(format!("{letter}:\\")));
                }
            }
        }
        None
    }
}

#[cfg(not(windows))]
mod platform {
    use std::env;
    use std::path::PathBuf;
    use std::process::Command;

    pub fn find_mount(label: &str) -> Option<PathBuf> {
        let user = env::var("USER").unwrap_or_default();
        for c in [
            format!("/Volumes/{label}"),
            format!("/run/media/{user}/{label}"),
            format!("/media/{user}/{label}"),
            format!("/media/{label}"),
        ] {
            let p = PathBuf::from(&c);
            if p.is_dir() {
                return Some(p);
            }
        }
        // Linux fallback: ask the OS where this label is mounted.
        if let Ok(out) = Command::new("findmnt")
            .args(["-rno", "TARGET", "-S", &format!("LABEL={label}")])
            .output()
        {
            if out.status.success() {
                if let Some(line) = String::from_utf8_lossy(&out.stdout).lines().next() {
                    let p = PathBuf::from(line.trim());
                    if p.is_dir() {
                        return Some(p);
                    }
                }
            }
        }
        None
    }
}

fn wait_mount(label: &str, timeout: u64) -> Option<PathBuf> {
    let deadline = Instant::now() + Duration::from_secs(timeout);
    while Instant::now() < deadline {
        if let Some(m) = platform::find_mount(label) {
            return Some(m);
        }
        sleep(Duration::from_millis(500));
    }
    None
}

fn wait_gone(label: &str, timeout: u64) {
    let deadline = Instant::now() + Duration::from_secs(timeout);
    while Instant::now() < deadline {
        if platform::find_mount(label).is_none() {
            return;
        }
        sleep(Duration::from_millis(500));
    }
}

// ---------- payload copy ----------
fn copy_dir(src: &Path, dst: &Path) -> io::Result<()> {
    fs::create_dir_all(dst)?;
    for entry in fs::read_dir(src)? {
        let entry = entry?;
        let from = entry.path();
        let to = dst.join(entry.file_name());
        if from.is_dir() {
            copy_dir(&from, &to)?;
        } else {
            fs::copy(&from, &to)?;
        }
    }
    Ok(())
}

fn copy_payload(cfg: &Config, dst: &Path) -> io::Result<()> {
    fs::copy(cfg.source.join("boot.py"), dst.join("boot.py"))?;
    fs::copy(cfg.source.join("code.py"), dst.join("code.py"))?;
    match &cfg.keys {
        Some(k) => {
            fs::copy(k, dst.join("keys.txt"))?;
        }
        None => {
            fs::copy(cfg.source.join("keys.txt"), dst.join("keys.txt"))?;
        }
    }
    copy_dir(&cfg.source.join("lib"), &dst.join("lib"))?;
    Ok(())
}

fn fail(msg: &str) -> ! {
    eprintln!("ERROR: {msg}");
    std::process::exit(2);
}

fn main() {
    let cfg = parse_args();

    // validate
    if !cfg.skip_fw {
        match &cfg.uf2 {
            None => fail("provide --uf2 <path>, or use --skip-firmware"),
            Some(u) if !Path::new(u).is_file() => fail(&format!("UF2 not found: {u}")),
            _ => {}
        }
    }
    if !cfg.source.is_dir() {
        fail(&format!("source folder not found: {}", cfg.source.display()));
    }
    for f in ["boot.py", "code.py", "keys.txt"] {
        if !cfg.source.join(f).is_file() {
            fail(&format!("missing payload file: {}", cfg.source.join(f).display()));
        }
    }
    if !cfg.source.join("lib").join("adafruit_hid").is_dir() {
        eprintln!(
            "WARNING: {}/adafruit_hid not found - code.py will crash without it.",
            cfg.source.join("lib").display()
        );
        eprintln!("         Copy the adafruit_hid folder in (circuitpython.org/libraries).");
    }
    if let Some(k) = &cfg.keys {
        if !Path::new(k).is_file() {
            fail(&format!("keys file not found: {k}"));
        }
    }

    println!("=== XIAO RP2040 batch flasher (rust) ===");
    println!("Source  : {}", cfg.source.display());
    println!(
        "Firmware: {}",
        if cfg.skip_fw { "(skipped)".into() } else { cfg.uf2.clone().unwrap() }
    );
    if let Some(k) = &cfg.keys {
        println!("Keys    : {k} (override)");
    }
    println!(
        "Boards  : {}\n",
        if cfg.count > 0 { cfg.count.to_string() } else { "loop until Ctrl+C".into() }
    );

    let mut done: i64 = 0;
    while cfg.count <= 0 || done < cfg.count {
        let n = done + 1;
        println!("--- Board #{n} ---");

        if !cfg.skip_fw {
            println!("Waiting for RPI-RP2 bootloader (hold BOOT + tap RESET, or plug in holding BOOT)...");
            let boot = match wait_mount("RPI-RP2", cfg.timeout) {
                Some(b) => b,
                None => {
                    println!("Timed out waiting for RPI-RP2; retrying.");
                    continue;
                }
            };
            println!("Writing firmware to {} ...", boot.display());
            let uf2 = cfg.uf2.as_ref().unwrap();
            let name = Path::new(uf2).file_name().unwrap();
            let _ = fs::copy(uf2, boot.join(name)); // drive vanishes as board reboots
            println!("Firmware written; board is rebooting...");
        }

        println!("Waiting for CIRCUITPY ...");
        let cp = match wait_mount("CIRCUITPY", cfg.timeout) {
            Some(c) => c,
            None => {
                println!("Timed out waiting for CIRCUITPY; retrying.");
                continue;
            }
        };

        println!("Copying payload to {} ...", cp.display());
        if let Err(e) = copy_payload(&cfg, &cp) {
            println!("Copy failed: {e}. Retrying this board.");
            continue;
        }
        println!("Board #{n} done. Safely eject, then unplug.");
        done += 1;

        if cfg.count > 0 && done >= cfg.count {
            break;
        }
        println!("Waiting for you to unplug this board...");
        wait_gone("CIRCUITPY", 3600);
        println!();
    }

    println!("\nFlashed {done} board(s).");
}
