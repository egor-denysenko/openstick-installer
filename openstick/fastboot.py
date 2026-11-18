"""Fastboot communication and management for OpenStick devices."""

import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple


@dataclass
class FastbootDevice:
    serial: str
    state: str = "fastboot"


def is_fastboot_available() -> bool:
    """Check if fastboot binary is installed and present in PATH."""
    return shutil.which("fastboot") is not None


def get_fastboot_devices() -> List[FastbootDevice]:
    """Execute 'fastboot devices' and parse connected devices."""
    if not is_fastboot_available():
        return []

    try:
        res = subprocess.run(
            ["fastboot", "devices"],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (subprocess.SubprocessError, FileNotFoundError):
        return []

    devices = []
    for line in res.stdout.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) >= 2:
            devices.append(FastbootDevice(serial=parts[0], state=parts[1]))
        elif len(parts) == 1:
            devices.append(FastbootDevice(serial=parts[0], state="fastboot"))
    return devices


def wait_for_device(timeout: int = 5) -> Optional[FastbootDevice]:
    """Poll for a connected fastboot device within timeout seconds."""
    start = time.time()
    while time.time() - start < timeout:
        devices = get_fastboot_devices()
        if devices:
            return devices[0]
        time.sleep(1)
    return None


def reboot_to_edl(serial: Optional[str] = None, dry_run: bool = False) -> bool:
    """
    Reboot connected device from fastboot into Qualcomm Emergency Download (EDL / 9008) mode.
    Tries in priority order:
      1. 'fastboot oem reboot-edl' (verified standard on MSM8916 OpenStick aboot bootloader)
      2. 'fastboot oem edl' (fallback)
      3. 'fastboot reboot-edl' (fallback on specific platform tools builds)
    """
    if dry_run:
        print("[DRY-RUN] Simulating 'fastboot oem reboot-edl'...")
        return True

    cmd_prefix = ["fastboot"]
    if serial:
        cmd_prefix.extend(["-s", serial])

    commands = [
        ["oem", "reboot-edl"],
        ["oem", "edl"],
        ["reboot-edl"],
    ]

    for cmd_args in commands:
        cmd = cmd_prefix + cmd_args
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            combined = (res.stdout + "\n" + res.stderr).lower()
            if "unknown command" in combined or "failed" in combined:
                continue
            if res.returncode == 0 or "okay" in combined:
                return True
        except subprocess.SubprocessError:
            continue

    return False


def reboot_bootloader(serial: Optional[str] = None, dry_run: bool = False) -> bool:
    """Reboot device back into bootloader / fastboot."""
    if dry_run:
        print("[DRY-RUN] Simulating 'fastboot reboot bootloader'...")
        return True

    cmd = ["fastboot"]
    if serial:
        cmd.extend(["-s", serial])
    cmd.extend(["reboot", "bootloader"])

    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        return res.returncode == 0
    except subprocess.SubprocessError:
        return False


def _fastboot_prefix(serial: Optional[str] = None) -> List[str]:
    cmd = ["fastboot"]
    if serial:
        cmd.extend(["-s", serial])
    return cmd


def _run_fastboot(cmd: List[str], timeout: int = 30) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def dump_partition(
    partition: str,
    output_path: Path,
    serial: Optional[str] = None,
    dry_run: bool = False,
) -> bool:
    """
    Dump a partition via the lk2nd/lk1st fastboot OEM extension:

        fastboot oem dump <partition>
        fastboot get_staged <output_path>

    This is a read-only diagnostic path that does not require EDL mode.
    Returns False when the OEM command is unsupported or the transfer fails.
    """
    if dry_run:
        print(f"[DRY-RUN] Simulating 'fastboot oem dump {partition}' -> {output_path}")
        return True

    if not is_fastboot_available():
        print("[-] fastboot binary not found in PATH.", file=sys.stderr)
        return False

    output_path = Path(output_path).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        res = _run_fastboot(_fastboot_prefix(serial) + ["oem", "dump", partition], timeout=20)
        combined = ((res.stdout or "") + "\n" + (res.stderr or "")).strip()
        if res.returncode != 0 or "unknown command" in combined.lower() or "failed" in combined.lower():
            print(f"[-] fastboot oem dump {partition} unsupported: {combined}", file=sys.stderr)
            return False

        res = _run_fastboot(_fastboot_prefix(serial) + ["get_staged", str(output_path)], timeout=120)
        if res.returncode != 0 or not output_path.is_file() or output_path.stat().st_size == 0:
            print(f"[-] fastboot get_staged failed for {partition}: {(res.stdout or '') + (res.stderr or '')}", file=sys.stderr)
            return False
        print(f"[+] Dumped '{partition}' to {output_path} ({output_path.stat().st_size} bytes)")
        return True
    except (subprocess.SubprocessError, OSError) as exc:
        print(f"[-] Fastboot dump of '{partition}' failed: {exc}", file=sys.stderr)
        return False


def get_lk_log(
    serial: Optional[str] = None,
    output_path: Optional[Path] = None,
    dry_run: bool = False,
) -> Tuple[bool, str]:
    """
    Retrieve the lk2nd/lk1st bootloader log via:

        fastboot oem lk_log
        fastboot get_staged /dev/stdout

    Returns (success, log_text). When output_path is given, the log is also saved.
    """
    if dry_run:
        return True, "[DRY-RUN] lk log"

    try:
        res = _run_fastboot(_fastboot_prefix(serial) + ["oem", "lk_log"], timeout=20)
        combined = ((res.stdout or "") + "\n" + (res.stderr or "")).strip()
        if res.returncode != 0 or "unknown command" in combined.lower():
            return False, combined

        res = _run_fastboot(_fastboot_prefix(serial) + ["get_staged", "/dev/stdout"], timeout=30)
        log_text = (res.stdout or "") + (res.stderr or "")
        if output_path:
            output_path = Path(output_path).expanduser().resolve()
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(log_text, errors="replace")
        return res.returncode == 0, log_text
    except (subprocess.SubprocessError, OSError) as exc:
        return False, str(exc)
