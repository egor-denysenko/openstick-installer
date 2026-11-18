"""Tests for Android boot.img parsing and appended DTB extraction."""

import struct
import tempfile
import unittest
from pathlib import Path

from openstick.bootimg import (
    FDT_MAGIC,
    extract_dtbs_from_boot_image,
    find_appended_dtbs,
    parse_dtb_info,
    read_boot_header,
)


def make_fdt(model="Test Board", compatible=("test,board", "qcom,msm8916")):
    """Build a minimal but valid flattened device tree with root model/compatible."""
    strings = b"model\0compatible\0"
    model_off = 0
    compat_off = 6

    def prop(nameoff, value):
        padded = value + b"\0" * ((4 - len(value) % 4) % 4)
        return struct.pack(">III", 3, len(value), nameoff) + padded

    block = (
        struct.pack(">I", 1) + b"\0\0\0\0"  # BEGIN_NODE root ("")
        + prop(model_off, model.encode() + b"\0")
        + prop(compat_off, b"\0".join(c.encode() for c in compatible) + b"\0")
        + struct.pack(">I", 2)  # END_NODE
        + struct.pack(">I", 9)  # END
    )
    off_struct = 40
    off_strings = off_struct + len(block)
    total = off_strings + len(strings)
    header = struct.pack(
        ">10I",
        0xD00DFEED,
        total,
        off_struct,
        off_strings,
        0,
        17,
        16,
        0,
        len(strings),
        len(block),
    )
    return header + block + strings


def make_boot_image(dtb, page_size=2048, cmdline="earlycon console=ttyMSM0,115200"):
    kernel = b"KERNEL-IMAGE" + dtb
    kernel_padded = kernel + b"\0" * ((-len(kernel)) % page_size)
    ramdisk = b"RAMDISK"
    ramdisk_padded = ramdisk + b"\0" * ((-len(ramdisk)) % page_size)

    header = bytearray(1604)
    header[0:8] = b"ANDROID!"
    struct.pack_into(
        ">8I",
        header,
        8,
        len(kernel),
        0x80008000,
        len(ramdisk),
        0x82000000,
        0,
        0,
        0x81E00000,
        page_size,
    )
    header[60 : 60 + len(cmdline)] = cmdline.encode()
    return bytes(header).ljust(page_size, b"\0") + kernel_padded + ramdisk_padded


class TestBootImage(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_read_boot_header(self):
        dtb = make_fdt()
        path = self.root / "boot.img"
        path.write_bytes(make_boot_image(dtb))
        header = read_boot_header(path)
        self.assertEqual(header["page_size"], 2048)
        self.assertEqual(header["kernel_size"], len(b"KERNEL-IMAGE") + len(dtb))
        self.assertEqual(header["ramdisk_size"], len(b"RAMDISK"))
        self.assertIn("ttyMSM0", header["cmdline"])
        self.assertEqual(header["header_version"], 0)

    def test_read_boot_header_rejects_non_boot_image(self):
        path = self.root / "bad.img"
        path.write_bytes(b"not a boot image" * 100)
        with self.assertRaises(ValueError):
            read_boot_header(path)

    def test_parse_dtb_info(self):
        info = parse_dtb_info(make_fdt("JZ08 4G Router", ("fy,jz08", "qcom,msm8916")))
        self.assertIsNotNone(info)
        self.assertEqual(info["model"], "JZ08 4G Router")
        self.assertEqual(info["compatible"], ["fy,jz08", "qcom,msm8916"])

    def test_parse_dtb_info_rejects_garbage(self):
        self.assertIsNone(parse_dtb_info(b"garbage"))

    def test_find_appended_dtbs_raw(self):
        dtb = make_fdt()
        blob = b"zImage-stuff" + dtb + b"trailing"
        found = find_appended_dtbs(blob)
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0][:4], FDT_MAGIC)

    def test_find_appended_dtbs_qcdt(self):
        dtb_a = make_fdt("Board A")
        dtb_b = make_fdt("Board B")
        header_len = 8 + 2 * 4
        off_a = header_len
        off_b = off_a + len(dtb_a)
        qcdt = b"QCDT" + struct.pack(">I", 2) + struct.pack(">II", off_a, off_b) + dtb_a + dtb_b
        found = find_appended_dtbs(qcdt)
        self.assertEqual(len(found), 2)
        self.assertEqual(parse_dtb_info(found[0])["model"], "Board A")
        self.assertEqual(parse_dtb_info(found[1])["model"], "Board B")

    def test_extract_dtbs_from_boot_image(self):
        dtb = make_fdt("JZ08 MIFI", ("fy,jz08", "qcom,msm8916"))
        boot_path = self.root / "boot.img"
        boot_path.write_bytes(make_boot_image(dtb))
        out_dir = self.root / "dtb"

        results = extract_dtbs_from_boot_image(boot_path, out_dir)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["model"], "JZ08 MIFI")
        self.assertIn("qcom,msm8916", results[0]["compatible"])
        written = Path(results[0]["path"])
        self.assertTrue(written.is_file())
        self.assertEqual(written.read_bytes(), dtb)


if __name__ == "__main__":
    unittest.main()
