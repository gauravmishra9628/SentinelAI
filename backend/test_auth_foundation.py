"""Focused regression checks for SentinelAI auth and provider safety."""

import os
import unittest

from ai import auth_service
from ai.dispatch_service import SimulationDispatchProvider, dispatch_status
from ai.location_service import SimulatedLocationProvider, unavailable_location


class AuthFoundationTests(unittest.TestCase):
    def setUp(self):
        self.previous_secret = os.environ.get("SENTINEL_AUTH_SECRET")
        os.environ["SENTINEL_AUTH_SECRET"] = "unit-test-secret-with-at-least-32-characters"

    def tearDown(self):
        if self.previous_secret is None:
            os.environ.pop("SENTINEL_AUTH_SECRET", None)
        else:
            os.environ["SENTINEL_AUTH_SECRET"] = self.previous_secret

    def test_password_hash_is_not_plaintext_and_token_validates(self):
        encoded = auth_service._hash_password("unit-test-password")
        self.assertNotIn("unit-test-password", encoded)
        self.assertTrue(auth_service._verify_password("unit-test-password", encoded))
        self.assertFalse(auth_service._verify_password("wrong-password", encoded))

        user = {"id": "test", "username": "tester", "role": "VIEWER"}
        token = auth_service.issue_token(user)
        self.assertEqual(token.count("."), 2)

    def test_simulated_location_has_no_coordinates(self):
        location = SimulatedLocationProvider().get_location("unit")
        self.assertEqual(location["source"], "SIMULATED")
        self.assertIsNone(location["latitude"])
        self.assertEqual(unavailable_location()["source"], "UNAVAILABLE")

    def test_dispatch_is_explicitly_simulated(self):
        result = SimulationDispatchProvider().dispatch("response", "unit", 10)
        self.assertEqual(result["mode"], "SIMULATED")
        self.assertTrue(dispatch_status()["safe_simulation"])


if __name__ == "__main__":
    unittest.main()
