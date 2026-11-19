# Handoff — JZ08 / "MIFI" board classification and image work

Date: 2026-11-19. Session ended with all code committed and pushed; **no device
operations were run in the last session** (user was short on time and will run them
later, possibly with another agent).

## 1. Goal

The user has an undocumented MSM8916 MiFi-style board (LCD + battery) that is **not**
HM-MIFIB / MF800. We want to (a) back it up safely, (b) identify it from its own device
tree, and (c) only then decide whether/how to build and flash a custom image.

Do **not** flash `openstick-hmmifib-linux.zip` on this device. Its DTB
(`msm8916-fy-mf800-fixed.dtb`) describes different LCD/battery/button wiring, and a
wrong DTB can soft-brick with no UART for recovery.

## 2. Where things live

| Path | Branch / role |
|---|---|
| `/home/bronco/projects/oss/openstick-installer-wt` | **primary session dir**, installer, `feature/generic-backup-mode`, commits `53ad558` + `e3aa7fe`, pushed to `origin` (`git@github.com:egor-denysenko/openstick-installer.git`). `upstream` = Basistiy/openstick-installer. Clean tree. |
| `/home/bronco/projects/oss/openstick-builder-wt` | builder, `feature/jz08-identification` (from main `5724497`). Remotes: `fork` = `git@github.com:egor-denysenko/openStick-Builder.git`, `origin` = kinsamanka upstream. **No commits, nothing pushed.** |
| `/home/bronco/projects/oss/openstick/docs/jz08-research.md` | research findings + source links (outside git; shared parent folder). |
| `/home/bronco/projects/oss/openstick/installer` | original installer worktree, `main`; ignore unless needed. |

Tests: `166 pass` via
`/home/bronco/projects/oss/openstick/installer/.venv/bin/python -m unittest discover -s tests`
(run from the worktree; the worktree has no `.venv` of its own — it is gitignored).

## 3. What we know about the device

Photos (LCD side + back side) show silkscreen:

- `JZ08V1.4-A-…`, `JZ08C_V5L 20260809 B01`, `20261005-JZ-10K-A`
- `JZ08D1_1 20260909 10P`

SoC marking: **QUALCOMM MSM8916**. SK hynix RAM, FORESEE storage (eMMC not yet confirmed
from a dump), SIM slot, ~128×128 LCD on FPC, battery connector, USB-C.

USB/ADB state at session end: `05c6:9024` in Android mode, `adb devices` → serial `0`.
ADB props (full dump was saved at `/tmp/opencode/jz08/props.txt`, may be gone):

```
ro.board.platform = msm8916
ro.product.model/device/name = MIFI
ro.product.board = msm8916
ro.hardware = qcom
ro.build.product = msm8916_32_512
ro.build.version.release = 4.4.4   (KTU84P test-keys)
```

Constraints discovered:

- `/sys/firmware/fdt`, `/proc/device-tree`, `/dev/dtb` do not exist (old vendor kernel).
- `adb shell` cannot read `/dev/block/bootdevice/by-name/*`; `adb root` is blocked.
- No UART. EDL is the only hard recovery path.
- Temporary EDL udev rule exists at `/run/udev/rules.d/99-edl.rules` and **vanishes on
  laptop reboot**; recreate with:
  ```bash
  sudo mkdir -p /run/udev/rules.d
  echo 'SUBSYSTEM=="usb", ATTR{idVendor}=="05c6", ATTR{idProduct}=="9008", MODE="0666", TAG+="uaccess"' | \
    sudo tee /run/udev/rules.d/99-edl.rules >/dev/null
  sudo udevadm control --reload-rules && sudo udevadm trigger
  ```
  (`TAG+="uaccess"` alone is not enough here; keep `MODE="0666"`. sudo needs a password.)

## 4. Research conclusions (details in `docs/jz08-research.md`)

- JZ08 appears in **no** supported-device list (openstick.de matrix, its forum search
  returns 0 hits, original KanCloud docs list only UFI001B/C, SP970, UZ801).
- Known DTBs: UZ801 → `msm8916-yiming-uz801v3.dtb`; UFI001B/C → `thwc-ufi001c.dtb`;
  MF800/MF800B-E → `fy-mf800.dtb`; JZ01-45 → `jz01-45-v33.dtb` (a *different*,
  screenless JZ board).
- Upstream pattern for unlisted boards: use generic base image and **replace
  `boot.img` with the board-specific one**. The DTB is appended to the kernel inside
  `boot.img` (KanCloud kernel-build guide: `cat Image.gz dtb > kernel-dtb`).
- MF800B-E saga warns: wrong DTB → soft brick; the LCD is **GC9107** (openstick.org says
  ST7735S for HM-MIFIB — unresolved for our board); charging needed a DTB phandle swap
  to fix an IRQ 30 conflict between `charger@1000` and `usb-detect@1300`.
- Original firmware files come from `/firmware/image/` on stock Android; incomplete
  sets are a classic reason the modem never registers.

## 5. Implemented tooling (installer branch)

- `openstick/devices.py`: `GENERIC_DEVICE` (`backup_only=True`), menu `[5]`, aliases
  `generic`/`unknown`/`unclassified`; device-specific prep/EDL steps for HM-MIFIB.
- `main.py --backup-only`: full eMMC dump + calibration, no flashing; captures ADB
  properties and `/firmware/image/` **before** entering EDL.
- `openstick/fastboot.py`: `dump_partition()` (`fastboot oem dump` + `get_staged`),
  `get_lk_log()`.
- `openstick/bootimg.py`: boot header parser, FDT/QCDT extractor, `model`/`compatible`
  reporter. Handles plain appended FDT and Qualcomm `QCDT`.
- `openstick/adb.py`: `dump_properties()`, `pull_firmware()`.
- CLI: `--inspect`, `--dump-partition NAME`, `--extract-dtb BOOT_IMG`.
  Artifacts: `diagnostics/<board>/` (gitignored).

## 6. Next actions, in order

1. **Recreate the udev rule if the laptop rebooted** (§3), confirm `adb devices`.
2. **Run read-only inspection while stock Android is still up:**
   ```bash
   cd /home/bronco/projects/oss/openstick-installer-wt
   python3 main.py --inspect --board generic
   ```
   This dumps `diagnostics/generic/properties.txt`, `firmware/`, `lk.log`, `boot.img`,
   and `dtb/*.dtb`. It may reboot the device into Fastboot and **leaves it there** —
   run `fastboot reboot` when finished.
3. If `fastboot oem dump` is unsupported on this stock bootloader, take the EDL dump
   instead and carve `boot` by GPT label (no hardcoded sector offsets):
   ```bash
   python3 main.py --backup-only
   cd /home/bronco/projects/oss/openstick-installer-wt
   python3 - <<'PY'
   from pathlib import Path
   from openstick.edl import parse_gpt_from_raw_image
   img = next(Path('backups').glob('generic_*/full_emmc.bin'))
   p = parse_gpt_from_raw_image(img)['boot']
   with img.open('rb') as f, open('boot.img','wb') as o:
       f.seek(p['byte_offset']); o.write(f.read(p['byte_size']))
   print('carved boot.img', p['byte_size'], 'bytes')
   PY
   python3 main.py --extract-dtb boot.img
   ```
4. **Read the DTB report.** Capture `model` and `compatible`; that is the board
   identity. Compare `dtb_*.dtb` with `builder/dtbs/msm8916-fy-mf800.dtb` and
   `msm8916-jz01-45-v33.dtb` (`dtc -I dtb -O dts | diff` is useful). Determine:
   - actual display controller (GC9107 vs ST7735S/ILI9163) and its SPI/GPIO lines;
   - battery charger / fuel-gauge nodes and their IRQ wiring;
   - whether the storage is really eMMC (check `edl printgpt` / dumped GPT).
5. **Classify then wire up:** add a JZ08 `DeviceModel` with the correct DTB and
   prep/EDL steps to `openstick/devices.py`; update README; add tests. Do **not**
   register a release asset until an image exists.
6. **Build only after classification:** decide between builder's fastboot flow and
   assembling a raw `full_emmc.bin` from the dump + builder output. If using the
   builder, set `LK2ND_COMPATIBLE` / `LK2ND_BUNDLE_DTB` and `configs/extlinux.conf`
   to the JZ08 DTB (builder defaults are UZ801 `yiming,uz801-v3`); note builder
   submodules are empty and test-signed aboot needs secure boot off.
7. Commit and push on `feature/generic-backup-mode`; builder work on
   `feature/jz08-identification` (push to `fork` when there is something to push).

## 7. Safety rules / do-nots

- Backup before anything; keep dumps labelled. A previous MF800 saga soft-bricked on
  a wrong DTB and recovery was only possible with a labelled EDL backup.
- Keep the battery installed and charged during dumps/flashes (this class can
  boot-loop on USB power alone).
- Never flash the HM-MIFIB image on this board.
- No UART — only SSH/fastboot diagnostics; do not rewrite the boot chain until the
  rollback dump is verified.
- `fastboot oem dump`, `fastboot oem lk_log` and `fastboot oem reboot-edl` are
  lk2nd/lk1st extensions; they may be absent on this stock bootloader. The EDL
  path always works as a fallback.

## 8. Open questions

- Does `fastboot oem dump boot` work on this stock aboot?
- What is the exact board `model`/`compatible` in the appended DTB?
- Which LCD controller and battery/IRQ wiring does JZ08 use?
- Is the storage eMMC (expected) or NAND? Confirm from the GPT before flashing.
- Does secure boot permit test-signed lk1st images on this unit?
- Should the installer grow a `--carve` helper (currently only on the separate
  `wip/installer-safety-and-images` branch) for offline rollback partitions?
