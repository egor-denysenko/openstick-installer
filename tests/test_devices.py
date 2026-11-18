"""Tests for device models and board definitions."""

import unittest
from openstick.devices import get_device_by_id, get_device_by_index, get_supported_devices


class TestDevices(unittest.TestCase):
    def test_get_supported_devices(self):
        devices = get_supported_devices()
        self.assertIn("uz801", devices)
        self.assertIn("hmuf02", devices)
        self.assertIn("hmmifib", devices)
        self.assertEqual(len(devices), 3)

    def test_get_uz801_by_id(self):
        dev = get_device_by_id("uz801")
        self.assertIsNotNone(dev)
        self.assertEqual(dev.id, "uz801")
        self.assertEqual(dev.recommended_loader, "prog_emmc_firehose_8916.mbn")
        self.assertIn("modemst1", dev.critical_partitions)
        self.assertIn("modemst2", dev.critical_partitions)
        self.assertIn("fsg", dev.critical_partitions)
        self.assertIn("fsc", dev.critical_partitions)

    def test_get_hmuf02_by_id_and_aliases(self):
        dev = get_device_by_id("hmuf02")
        self.assertIsNotNone(dev)
        self.assertEqual(dev.id, "hmuf02")
        self.assertEqual(dev.recommended_loader, "prog_emmc_firehose_8916.mbn")
        for part in ("modemst1", "modemst2", "fsg", "fsc", "persist", "sec"):
            self.assertIn(part, dev.critical_partitions)

        for alias in ("HMUF02", "hmuf", "HMUF02-V05"):
            resolved = get_device_by_id(alias)
            self.assertIsNotNone(resolved)
            self.assertEqual(resolved.id, "hmuf02")

    def test_get_hmmifib_by_id_and_aliases(self):
        dev = get_device_by_id("hmmifib")
        self.assertIsNotNone(dev)
        self.assertEqual(dev.id, "hmmifib")
        self.assertEqual(dev.recommended_loader, "prog_emmc_firehose_8916.mbn")
        for part in ("modemst1", "modemst2", "fsg", "fsc", "persist", "sec"):
            self.assertIn(part, dev.critical_partitions)

        for alias in ("HMMIFIB", "HM-MIFIB", "hm-mifib", "mifib", "mf800", "MF800"):
            resolved = get_device_by_id(alias)
            self.assertIsNotNone(resolved)
            self.assertEqual(resolved.id, "hmmifib")

    def test_hmmifib_has_device_specific_steps(self):
        dev = get_device_by_id("hmmifib")
        self.assertGreaterEqual(len(dev.prep_steps), 3)
        self.assertGreaterEqual(len(dev.edl_entry_steps), 3)
        self.assertTrue(any("battery" in step.lower() for step in dev.prep_steps))
        self.assertTrue(any("edl" in step.lower() for step in dev.edl_entry_steps))
        command_names = [command for command, _ in dev.post_install_tools]
        for tool in ("battery", "lcd-show", "lte", "usb-mode"):
            self.assertIn(tool, " ".join(command_names))

    def test_generic_backup_only_device(self):
        dev = get_device_by_id("generic")
        self.assertIsNotNone(dev)
        self.assertTrue(dev.backup_only)
        self.assertFalse(dev.post_install_tools)
        self.assertTrue(any("dump" in step.lower() for step in dev.prep_steps))

        for alias in ("GENERIC", "unknown", "unclassified", "backup-only"):
            resolved = get_device_by_id(alias)
            self.assertIsNotNone(resolved)
            self.assertEqual(resolved.id, "generic")

        self.assertEqual(get_device_by_index(5).id, "generic")
        self.assertIsNone(get_device_by_index(6))

    def test_case_insensitivity(self):
        dev_upper = get_device_by_id("UZ801")
        self.assertIsNotNone(dev_upper)
        self.assertEqual(dev_upper.id, "uz801")

        dev_mixed = get_device_by_id("  Uz801  ")
        self.assertIsNotNone(dev_mixed)
        self.assertEqual(dev_mixed.id, "uz801")

    def test_unknown_device_returns_none(self):
        self.assertIsNone(get_device_by_id("unknown_board"))
        self.assertIsNone(get_device_by_id(""))

    def test_get_by_index(self):
        dev1 = get_device_by_index(1)
        self.assertIsNotNone(dev1)
        self.assertEqual(dev1.id, "uz801")

        dev2 = get_device_by_index(2)
        self.assertIsNotNone(dev2)
        self.assertEqual(dev2.id, "hmuf02")

        dev3 = get_device_by_index(3)
        self.assertIsNotNone(dev3)
        self.assertEqual(dev3.id, "hmmifib")

        dev4 = get_device_by_index(4)
        self.assertIsNotNone(dev4)
        self.assertEqual(dev4.id, "custom")

        self.assertIsNone(get_device_by_index(0))
        self.assertIsNone(get_device_by_index(99))

    def test_get_custom_device_by_id_and_aliases(self):
        dev = get_device_by_id("custom")
        self.assertIsNotNone(dev)
        self.assertEqual(dev.id, "custom")
        self.assertEqual(dev.recommended_loader, "prog_emmc_firehose_8916.mbn")

        for alias in ("custom-image", "custom_image", "other", "CUSTOM"):
            resolved = get_device_by_id(alias)
            self.assertIsNotNone(resolved)
            self.assertEqual(resolved.id, "custom")


if __name__ == "__main__":
    unittest.main()
