import unittest

from app.engine import process_screen_text, process_visual, supported_flow


class SpectreEngineTest(unittest.TestCase):
    def test_enterprise_kyc_keeps_raw_data_out_of_destination(self):
        result = process_visual("enterprise_kyc", ["id_card", "nik"])

        self.assertTrue(result["source"]["raw_data_received"])
        self.assertFalse(result["destination"]["receives_raw_data"])
        self.assertTrue(result["destination"]["storage_policy"]["sovereign_vault_persisted"])
        self.assertEqual(result["middleware"]["redaction"]["redacted_count"], 2)

    def test_live_shield_is_ephemeral(self):
        result = process_visual("liveshield", ["face"])

        self.assertFalse(result["destination"]["storage_policy"]["operational_zone_persisted"])
        self.assertFalse(result["audit"]["raw_data_left_source"])

    def test_screen_shield_redacts_sensitive_text(self):
        result = process_screen_text("NIK 3276010101010001 gaji Rp 12.000.000")

        self.assertNotIn("3276010101010001", result["destination"]["redacted_text"])
        self.assertNotIn("12.000.000", result["destination"]["redacted_text"])
        self.assertEqual(result["middleware"]["redaction"]["redacted_count"], 2)

    def test_flow_lists_three_tracks(self):
        self.assertEqual(set(supported_flow()["tracks"]), {"enterprise_kyc", "liveshield", "screen_shield"})


if __name__ == "__main__":
    unittest.main()
