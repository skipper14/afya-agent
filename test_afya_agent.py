import unittest

from afya_agent import calculate_metric, mask_pii, unmask_output


class AfyaAgentTests(unittest.TestCase):
    def test_mask_and_unmask_text(self) -> None:
        original = "Please call +254701234567 or email support@afya.org"
        masked, replacements = mask_pii(original)

        self.assertIn("[PHONE_1]", masked)
        self.assertIn("[EMAIL_1]", masked)
        self.assertEqual(replacements["[PHONE_1]"], "+254701234567")
        self.assertEqual(replacements["[EMAIL_1]"], "support@afya.org")

        restored = unmask_output(masked, replacements)
        self.assertEqual(restored, original)

    def test_calculate_metric_tool(self) -> None:
        result = calculate_metric(operation="dose_volume", volume_ml=100.0, concentration_mg_per_ml=5.0)

        self.assertEqual(result["operation"], "dose_volume")
        self.assertEqual(result["result"], 500.0)


if __name__ == "__main__":
    unittest.main()
