"""Device models registry and hardware definitions for MSM8916 USB sticks."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class DeviceModel:
    id: str
    name: str
    description: str
    soc: str = "Qualcomm MSM8916 (Snapdragon 410)"
    ram: str = "512MB / 1GB LPDDR3"
    storage: str = "4GB eMMC"
    default_gateway: str = "192.168.100.1"
    adb_enable_url: str = "http://192.168.100.1/usbdebug.html"
    recommended_loader: str = "prog_emmc_firehose_8916.mbn"
    critical_partitions: List[str] = field(
        default_factory=lambda: ["modemst1", "modemst2", "fsg", "fsc", "persist", "sec"]
    )
    notes: List[str] = field(default_factory=list)
    # Device-specific checklist shown right after board selection. Keeps the
    # installer actionable for boards whose hardware differs from a plain dongle.
    prep_steps: List[str] = field(default_factory=list)
    # Hardware EDL entry procedure. When empty, ui.show_adb_guidance() falls back
    # to the generic recovery-button / EDL-pads instructions.
    edl_entry_steps: List[str] = field(default_factory=list)
    # Post-flash tools, as (command, description) pairs, added to the summary.
    post_install_tools: List[Tuple[str, str]] = field(default_factory=list)
    # Backup-only utility mode: dump/restore stock eMMC for an unclassified board.
    # No release image is downloaded or flashed for these devices.
    backup_only: bool = False


# Supported devices registry
DEVICES: Dict[str, DeviceModel] = {
    "uz801": DeviceModel(
        id="uz801",
        name="UZ801 (4G LTE USB Modem Dongle)",
        description="Common white USB dongle with SIM slot and Qualcomm MSM8916 SoC.",
        default_gateway="192.168.100.1",
        adb_enable_url="http://192.168.100.1/usbdebug.html",
        recommended_loader="prog_emmc_firehose_8916.mbn",
        critical_partitions=["modemst1", "modemst2", "fsg", "fsc", "persist", "sec"],
        notes=[
            "To enable ADB: Connect to its Wi-Fi, open http://192.168.100.1/usbdebug.html in a browser, and toggle USB debug on.",
            "Fastboot reboot command: fastboot oem reboot-edl transitions directly to EDL mode.",
            "If soft-reboot to EDL fails: Hold physical recovery button or short EDL pins while plugging into USB.",
            "Critical calibration partitions: modemst1, modemst2, fsg, fsc, persist, sec (contain unique IMEI and RF calibration).",
        ],
        prep_steps=[
            "Use a short, data-capable USB cable directly on the PC (no hub) so the stick stays in EDL for the whole flash.",
            "On stock firmware the stick is usually ADB-enabled already; check 'adb devices' before opening any casing.",
            "If ADB is missing, join its Wi-Fi and open http://192.168.100.1/usbdebug.html to toggle USB Debug ON.",
        ],
    ),
    "hmuf02": DeviceModel(
        id="hmuf02",
        name="HMUF02 (4G LTE USB Modem Dongle)",
        description="Qualcomm MSM8916 4G LTE Wi-Fi USB dongle (commonly HMUF02-V05 PCB revision).",
        ram="512MB LPDDR3",
        storage="4GB eMMC",
        default_gateway="192.168.100.1",
        adb_enable_url="http://192.168.100.1",
        recommended_loader="prog_emmc_firehose_8916.mbn",
        critical_partitions=["modemst1", "modemst2", "fsg", "fsc", "persist", "sec"],
        notes=[
            "Stock ADB: Plug into USB and check 'adb devices' (or check USB debug settings in the stock Web UI at http://192.168.100.1).",
            "Fastboot reboot command: fastboot oem reboot-edl transitions directly to EDL mode.",
            "If soft-reboot to EDL fails: Hold physical reset/recovery button or short EDL test pads while plugging into USB.",
            "Critical calibration partitions: modemst1, modemst2, fsg, fsc, persist, sec (contain unique IMEI and RF calibration).",
        ],
        prep_steps=[
            "Use a short, data-capable USB cable directly on the PC (no hub) so the stick stays in EDL for the whole flash.",
            "On stock firmware plug into USB and check 'adb devices'; otherwise enable USB debugging in the stock Web UI at http://192.168.100.1.",
            "Keep the stick powered from the PC (or its own supply) from the backup step through the final reboot.",
        ],
    ),
    "hmmifib": DeviceModel(
        id="hmmifib",
        name="HM-MIFIB (4G LTE Mobile Wi-Fi Router)",
        description="Qualcomm MSM8916 4G LTE portable Wi-Fi router with battery and 128x128 ST7735S LCD (MF800).",
        ram="512MB LPDDR3",
        storage="4GB eMMC",
        default_gateway="192.168.100.1",
        adb_enable_url="http://192.168.100.1",
        recommended_loader="prog_emmc_firehose_8916.mbn",
        critical_partitions=["modemst1", "modemst2", "fsg", "fsc", "persist", "sec"],
        notes=[
            "Stock ADB: Plug into USB and check 'adb devices' (or enable USB debugging via the stock Web UI at http://192.168.100.1).",
            "Fastboot reboot command: fastboot oem reboot-edl transitions directly to EDL mode.",
            "If soft-reboot to EDL fails: Remove battery, hold reset/recovery button (or short EDL pads) while plugging into USB.",
            "Critical calibration partitions: modemst1, modemst2, fsg, fsc, persist, sec (contain unique IMEI and RF calibration).",
        ],
        prep_steps=[
            "KEEP THE BATTERY INSTALLED AND CHARGED (at least ~3.8V). This board can boot-loop on USB power alone: "
            "the MSM8916 inrush spike exceeds what a 500 mA USB 2.0 port can supply, and the battery acts as the reservoir.",
            "Power on by holding the physical Power button for ~3 seconds; the 1.44\" LCD should light up. "
            "A short press of the same button toggles the backlight.",
            "Connect a data-capable USB cable directly to the PC (no hub). On stock firmware check 'adb devices'; "
            "if ADB is missing, enable USB debugging via the stock Web UI at http://192.168.100.1.",
            "Take the calibration backup before flashing. The LCD/battery board carries the same unique IMEI and RF "
            "calibration (modemst1, modemst2, fsg, fsc, persist, sec) as the headless dongles.",
        ],
        edl_entry_steps=[
            "Power the device off, then remove the battery.",
            "Connect the USB cable from the PC to the device (leave the battery out for now).",
            "Locate the two small gold EDL test pads in the battery bay, near the SIM slot.",
            "Short the two pads with tweezers, then insert the battery (or apply 5V USB power) while keeping the short.",
            "Hold for about 2 seconds, then remove the short. Confirm with: lsusb | grep 05c6:9008",
        ],
        post_install_tools=[
            ("battery", "capacity %, voltage and charging status"),
            ("lcd-show <status|glosos|wave|on|off> (or lcd_ctl)", "128x128 ST7735S LCD and backlight"),
            ("lte", "SIM state, signal strength and LTE IP"),
            ("usb-mode <status|gadget|host>", "switch USB between gadget (network) and host"),
        ],
    ),
}

CUSTOM_DEVICE = DeviceModel(
    id="custom",
    name="Custom Image (MSM8916)",
    description="Generic Qualcomm MSM8916 device using a user-provided custom Linux image.",
    soc="Qualcomm MSM8916 (Snapdragon 410)",
    ram="512MB / 1GB / 2GB LPDDR3",
    storage="4GB / 8GB eMMC",
    default_gateway="192.168.100.1 (or 192.168.5.1 / 192.168.68.1)",
    adb_enable_url="http://192.168.100.1",
    recommended_loader="prog_emmc_firehose_8916.mbn",
    critical_partitions=["modemst1", "modemst2", "fsg", "fsc", "persist", "sec"],
    notes=[
        "Generic MSM8916 device flow with a custom raw eMMC Linux image (.bin or .zip).",
        "Stock ADB: Connect PC to stick's Wi-Fi network and toggle USB debugging in the web panel.",
        "Fastboot reboot command: fastboot oem reboot-edl transitions directly to EDL mode.",
        "If soft-reboot to EDL fails: Hold physical recovery button or short EDL test pads while plugging into USB.",
        "You will be asked for the path to your custom image when installing Linux.",
        "Unique cellular calibration partitions will be backed up and injected into the custom image.",
    ],
)

GENERIC_DEVICE = DeviceModel(
    id="generic",
    name="Generic / unclassified MSM8916 (backup & restore only)",
    description="Unknown MSM8916 board: dump stock eMMC and calibration before classification. No firmware install is offered.",
    ram="512MB / 1GB LPDDR3",
    storage="4GB / 8GB eMMC",
    notes=[
        "BACKUP-ONLY MODE: the installer will dump the full eMMC and slice the calibration partitions, then stop.",
        "Use this for boards that are not yet identified (e.g. undocumented JZxx variants) before choosing a DTB or image.",
        "You can restore the dump later with 'python3 main.py --board generic' and choosing [2] Restore Stock Backup.",
        "Record the PCB silkscreen, SoC marking and ADB properties (getprop ro.board.platform / ro.product.model) for classification.",
    ],
    prep_steps=[
        "This mode does NOT flash anything: it only reads the eMMC via Qualcomm 9008 EDL and writes backups/ + calibration/.",
        "Keep the board powered for the whole dump; use a short data-capable USB cable directly on the PC (no hub).",
        "If stock firmware boots, capture 'adb shell getprop ro.board.platform', 'ro.product.model' and 'adb pull /sys/firmware/fdt' first — they identify the board and its device tree.",
    ],
    backup_only=True,
)


DEVICE_ALIASES: Dict[str, str] = {
    "generic": "generic",
    "unknown": "generic",
    "unclassified": "generic",
    "backup-only": "generic",
    "uz801-v3": "uz801",
    "hmuf": "hmuf02",
    "hmuf02-v05": "hmuf02",
    "hm-mifib": "hmmifib",
    "mifib": "hmmifib",
    "mf800": "hmmifib",
    "custom-image": "custom",
    "custom_image": "custom",
    "other": "custom",
}


def get_supported_devices() -> Dict[str, DeviceModel]:
    """Return all currently supported devices."""
    return DEVICES


def get_device_by_id(device_id: str) -> Optional[DeviceModel]:
    """Retrieve device by its string identifier or alias (case-insensitive)."""
    key = device_id.lower().strip()
    key = DEVICE_ALIASES.get(key, key)
    if key == "custom":
        return CUSTOM_DEVICE
    if key == "generic":
        return GENERIC_DEVICE
    return DEVICES.get(key)


def get_device_by_index(idx: int) -> Optional[DeviceModel]:
    """Retrieve device by 1-based index corresponding to menu list."""
    keys = list(DEVICES.keys())
    if 1 <= idx <= len(keys):
        return DEVICES[keys[idx - 1]]
    if idx == len(keys) + 1:
        return CUSTOM_DEVICE
    if idx == len(keys) + 2:
        return GENERIC_DEVICE
    return None
