"""Android boot.img inspection and appended device-tree extraction.

MSM8916 OpenStick boot images concatenate the DTB to the kernel before calling
mkbootimg (see the original KanCloud kernel-build guide), so the board's device
tree must be recovered from the boot partition rather than from a separate file.
"""

import struct
from pathlib import Path
from typing import Dict, List, Optional

BOOT_MAGIC = b"ANDROID!"
FDT_MAGIC = b"\xd0\x0d\xfe\xed"
QCDT_MAGIC = b"QCDT"

FDT_BEGIN_NODE = 1
FDT_END_NODE = 2
FDT_PROP = 3
FDT_NOP = 4
FDT_END = 9


def read_boot_header(image_path: Path) -> Dict:
    """Parse the legacy (v0/v1) Android boot image header."""
    with open(image_path, "rb") as fh:
        raw = fh.read(2048)
    if len(raw) < 40 or raw[:8] != BOOT_MAGIC:
        raise ValueError("Not an Android boot image (missing ANDROID! magic)")

    (
        kernel_size,
        kernel_addr,
        ramdisk_size,
        ramdisk_addr,
        second_size,
        second_addr,
        tags_addr,
        page_size,
    ) = struct.unpack(">8I", raw[8:40])
    if page_size == 0:
        raise ValueError("Invalid boot image: page_size is zero")

    header_version = struct.unpack(">I", raw[1604:1608])[0] if len(raw) >= 1608 else 0
    cmdline = raw[60:572].split(b"\0", 1)[0].decode("utf-8", "replace")
    return {
        "kernel_size": kernel_size,
        "kernel_addr": kernel_addr,
        "ramdisk_size": ramdisk_size,
        "ramdisk_addr": ramdisk_addr,
        "second_size": second_size,
        "second_addr": second_addr,
        "tags_addr": tags_addr,
        "page_size": page_size,
        "header_version": header_version,
        "cmdline": cmdline,
    }


def parse_dtb_info(dtb: bytes) -> Optional[Dict]:
    """Extract size, root `model` and `compatible` strings from a flattened DTB."""
    if len(dtb) < 40 or dtb[:4] != FDT_MAGIC:
        return None

    (
        totalsize,
        off_dt_struct,
        off_dt_strings,
        _off_dt_mem,
        _version,
        _last_comp,
        _boot_cpuid,
        size_dt_strings,
        size_dt_struct,
    ) = struct.unpack(">9I", dtb[4:40])

    strings = dtb[off_dt_strings : off_dt_strings + size_dt_strings]
    block = dtb[off_dt_struct : off_dt_struct + size_dt_struct]

    info: Dict = {"size": totalsize, "model": None, "compatible": [], "root_node": None}
    pos = 0
    depth = -1
    while pos + 4 <= len(block):
        token = struct.unpack(">I", block[pos : pos + 4])[0]
        pos += 4
        if token == FDT_BEGIN_NODE:
            end = block.find(b"\0", pos)
            if end < 0:
                break
            name = block[pos:end].decode("utf-8", "replace")
            pos = (end + 4) & ~3
            depth += 1
            if depth == 0:
                info["root_node"] = name or "/"
        elif token == FDT_END_NODE:
            depth -= 1
        elif token == FDT_PROP:
            if pos + 8 > len(block):
                break
            length, nameoff = struct.unpack(">II", block[pos : pos + 8])
            pos += 8
            value = block[pos : pos + length]
            pos = (pos + length + 3) & ~3
            nend = strings.find(b"\0", nameoff) if nameoff < len(strings) else -1
            prop = strings[nameoff:nend].decode("utf-8", "replace") if nend >= 0 else ""
            if depth == 0 and prop == "model":
                info["model"] = value.rstrip(b"\0").decode("utf-8", "replace")
            elif depth == 0 and prop == "compatible":
                info["compatible"] = [s.decode("utf-8", "replace") for s in value.split(b"\0") if s]
        elif token == FDT_NOP:
            continue
        elif token == FDT_END:
            break
        else:
            break

    return info


def find_appended_dtbs(blob: bytes) -> List[bytes]:
    """Find FDT blobs appended to a kernel, including Qualcomm QCDT tables."""
    if blob.startswith(QCDT_MAGIC) and len(blob) >= 8:
        count = struct.unpack(">I", blob[4:8])[0]
        if 0 < count <= 64 and len(blob) >= 8 + 4 * count:
            offsets = struct.unpack(f">{count}I", blob[8 : 8 + 4 * count])
            found = []
            for offset in offsets:
                if offset + 8 > len(blob) or blob[offset : offset + 4] != FDT_MAGIC:
                    continue
                size = struct.unpack(">I", blob[offset + 4 : offset + 8])[0]
                if 40 <= size <= len(blob) - offset:
                    found.append(blob[offset : offset + size])
            if found:
                return found

    found = []
    pos = 0
    while True:
        pos = blob.find(FDT_MAGIC, pos)
        if pos < 0:
            break
        if pos + 8 <= len(blob):
            size = struct.unpack(">I", blob[pos + 4 : pos + 8])[0]
            if 40 <= size <= len(blob) - pos:
                found.append(blob[pos : pos + size])
                pos += size
                continue
        pos += 4
    return found


def extract_dtbs_from_boot_image(
    image_path: Path,
    output_dir: Path,
    dry_run: bool = False,
) -> List[Dict]:
    """
    Extract every DTB appended to a boot image kernel into output_dir.

    Returns a list of dicts with: path, size, model, compatible, index.
    """
    header = read_boot_header(image_path)
    if dry_run:
        return [
            {
                "path": None,
                "size": 0,
                "model": "[DRY-RUN] unknown",
                "compatible": [],
                "index": 0,
            }
        ]

    kernel_offset = header["page_size"]
    with open(image_path, "rb") as fh:
        fh.seek(kernel_offset)
        kernel = fh.read(header["kernel_size"])
        second = b""
        if header["second_size"]:
            second_offset = kernel_offset + (
                (header["kernel_size"] + header["page_size"] - 1) // header["page_size"]
            ) * header["page_size"]
            second_offset += (
                (header["ramdisk_size"] + header["page_size"] - 1) // header["page_size"]
            ) * header["page_size"]
            fh.seek(second_offset)
            second = fh.read(header["second_size"])

    dtbs = find_appended_dtbs(kernel) or find_appended_dtbs(second)
    output_dir = Path(output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    results = []
    for idx, dtb in enumerate(dtbs):
        info = parse_dtb_info(dtb) or {}
        out_path = output_dir / f"dtb_{idx:02d}.dtb"
        out_path.write_bytes(dtb)
        results.append(
            {
                "path": str(out_path),
                "size": len(dtb),
                "model": info.get("model"),
                "compatible": info.get("compatible", []),
                "index": idx,
            }
        )
    return results
