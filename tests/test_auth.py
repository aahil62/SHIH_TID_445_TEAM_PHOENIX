import unittest

from fraudlens.testing import use_isolated_data_dir

use_isolated_data_dir()

from fastapi.testclient import TestClient

from fraudlens.api.main import app


class AuthTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)
        cls.client.__enter__()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.client.__exit__(None, None, None)

    def test_login_with_seeded_account_succeeds(self) -> None:
        resp = self.client.post("/auth/login", json={"username": "asharma", "password": "fraudlens123"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["access_token"])
        self.assertEqual(data["analyst"]["username"], "asharma")
        self.assertEqual(data["analyst"]["display_name"], "A. Sharma")

    def test_login_with_wrong_password_rejected(self) -> None:
        resp = self.client.post("/auth/login", json={"username": "asharma", "password": "wrong"})
        self.assertEqual(resp.status_code, 401)

    def test_login_with_unknown_username_rejected(self) -> None:
        resp = self.client.post("/auth/login", json={"username": "nobody", "password": "whatever"})
        self.assertEqual(resp.status_code, 401)

    def test_signup_creates_a_real_account_that_can_then_log_in(self) -> None:
        signup = self.client.post(
            "/auth/signup",
            json={"username": "newanalyst", "display_name": "N. Verma", "password": "supersecret1"},
        )
        self.assertEqual(signup.status_code, 200)
        self.assertEqual(signup.json()["analyst"]["display_name"], "N. Verma")

        login = self.client.post("/auth/login", json={"username": "newanalyst", "password": "supersecret1"})
        self.assertEqual(login.status_code, 200)

    def test_signup_with_taken_username_rejected(self) -> None:
        resp = self.client.post(
            "/auth/signup",
            json={"username": "asharma", "display_name": "Someone Else", "password": "whatever1"},
        )
        self.assertEqual(resp.status_code, 409)

    def test_signup_with_short_password_rejected(self) -> None:
        resp = self.client.post(
            "/auth/signup", json={"username": "shortpw", "display_name": "X", "password": "abc"}
        )
        self.assertEqual(resp.status_code, 400)

    def test_me_requires_a_valid_token(self) -> None:
        resp = self.client.get("/auth/me")
        self.assertEqual(resp.status_code, 401)

        resp = self.client.get("/auth/me", headers={"Authorization": "Bearer not-a-real-token"})
        self.assertEqual(resp.status_code, 401)

    def test_me_returns_the_logged_in_analyst(self) -> None:
        login = self.client.post("/auth/login", json={"username": "riyer", "password": "fraudlens123"})
        token = login.json()["access_token"]

        resp = self.client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["username"], "riyer")

    def test_submit_decision_without_auth_is_rejected(self) -> None:
        txn_id = self.client.get("/transactions/recent?limit=1").json()["transactions"][0]["txn_id"]
        resp = self.client.post("/decisions", json={"txn_id": txn_id, "decision": "review"})
        self.assertEqual(resp.status_code, 401)

    def test_submit_decision_with_auth_records_the_real_authenticated_analyst(self) -> None:
        login = self.client.post("/auth/login", json={"username": "asharma", "password": "fraudlens123"})
        token = login.json()["access_token"]

        txn_id = self.client.get("/transactions/recent?limit=2").json()["transactions"][1]["txn_id"]
        resp = self.client.post(
            "/decisions",
            json={"txn_id": txn_id, "decision": "review", "notes": "checking in"},
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(resp.status_code, 200)
        # The analyst name comes from the authenticated session, not
        # anything the client could have claimed in the request body —
        # DecisionRequest no longer even accepts an `analyst` field.
        self.assertEqual(resp.json()["analyst"], "A. Sharma")

    def test_decision_request_ignores_any_client_supplied_analyst_field(self) -> None:
        """Defense in depth: even if a client sends an `analyst` key in the
        body (stale frontend, hand-crafted request), it must have zero
        effect — the schema doesn't declare the field, so FastAPI/Pydantic
        drops it, and the real identity always comes from the token."""
        login = self.client.post("/auth/login", json={"username": "riyer", "password": "fraudlens123"})
        token = login.json()["access_token"]

        txn_id = self.client.get("/transactions/recent?limit=3").json()["transactions"][2]["txn_id"]
        resp = self.client.post(
            "/decisions",
            json={"txn_id": txn_id, "decision": "clear", "analyst": "Someone Impersonated"},
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["analyst"], "R. Iyer")


if __name__ == "__main__":
    unittest.main()
