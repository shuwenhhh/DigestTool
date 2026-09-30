import unittest

from digest.config_loader import load_phase_weights, load_role_weights


class ConfigLoaderTests(unittest.TestCase):
    def test_loads_electrical_engineer_and_dvt(self) -> None:
        role_name, role_weights = load_role_weights("electrical_engineer")
        phase_name, phase_weights = load_phase_weights("DVT")
        self.assertEqual(role_name, "Electrical Engineer")
        self.assertEqual(phase_name, "DVT")
        self.assertEqual(role_weights["TEST_RESULT"], 1.5)
        self.assertEqual(phase_weights["TEST_RESULT"], 1.4)

    def test_unknown_profile_is_clear(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unknown profile"):
            load_role_weights("astronaut")


if __name__ == "__main__":
    unittest.main()
