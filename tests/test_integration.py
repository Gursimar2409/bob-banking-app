"""
test_integration.py
-------------------
Integration tests: exercises Flask routes end-to-end against a
temporary SQLite database (not bank.db).

Each test class gets a fresh Flask test client backed by an isolated
temp-file database so tests are fully independent.
"""

import os
import sys
import tempfile

import pytest

# BACKEND/ is on sys.path via conftest.py


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def client(tmp_path, monkeypatch):
    """Yield a Flask test client backed by an isolated temp database."""
    # Point DB_PATH at a temp file before importing anything from BACKEND/
    db_file = str(tmp_path / "test_bank.db")
    import database as db_module
    monkeypatch.setattr(db_module, "DB_PATH", db_file)

    # Re-initialise the temp database
    db_module.init_db()

    # Import app AFTER patching the DB path so it uses the temp db
    import app as app_module
    monkeypatch.setattr(app_module, "init_db", lambda: None)  # already done
    app_module.app.config["TESTING"] = True
    app_module.app.config["SECRET_KEY"] = "test-secret"
    app_module.app.config["WTF_CSRF_ENABLED"] = False

    with app_module.app.test_client() as c:
        yield c


def _login(client, username="alice", password="password123"):
    """Helper: POST credentials and return the response."""
    return client.post(
        "/login",
        data={"username": username, "password": password},
        follow_redirects=False,
    )


# ---------------------------------------------------------------------------
# 1. Login page
# ---------------------------------------------------------------------------

class TestLoginPage:
    def test_get_login_returns_200(self, client):
        resp = client.get("/login")
        assert resp.status_code == 200

    def test_login_page_contains_sign_in(self, client):
        resp = client.get("/login")
        assert b"Sign In" in resp.data

    def test_root_redirects_to_login(self, client):
        resp = client.get("/", follow_redirects=False)
        assert resp.status_code in (301, 302)
        assert "/login" in resp.headers["Location"]


# ---------------------------------------------------------------------------
# 2. Authentication — valid credentials
# ---------------------------------------------------------------------------

class TestLoginValid:
    def test_valid_login_redirects_to_dashboard(self, client):
        resp = _login(client)
        assert resp.status_code == 302
        assert "/dashboard" in resp.headers["Location"]

    def test_session_contains_user_id_after_login(self, client):
        import app as app_module
        with app_module.app.test_client() as c:
            with c.session_transaction() as sess:
                sess.clear()
            c.post("/login", data={"username": "alice", "password": "password123"})
            with c.session_transaction() as sess:
                assert "user_id" in sess


# ---------------------------------------------------------------------------
# 3. Authentication — invalid credentials
# ---------------------------------------------------------------------------

class TestLoginInvalid:
    def test_wrong_password_returns_200(self, client):
        resp = client.post(
            "/login",
            data={"username": "alice", "password": "wrongpass"},
            follow_redirects=False,
        )
        assert resp.status_code == 200

    def test_wrong_password_shows_error(self, client):
        resp = client.post(
            "/login",
            data={"username": "alice", "password": "wrongpass"},
        )
        assert b"Invalid credentials" in resp.data

    def test_unknown_username_shows_same_error(self, client):
        resp = client.post(
            "/login",
            data={"username": "nobody", "password": "whatever"},
        )
        assert b"Invalid credentials" in resp.data

    def test_empty_fields_shows_error(self, client):
        resp = client.post("/login", data={"username": "", "password": ""})
        assert resp.status_code == 200
        assert b"Please enter" in resp.data


# ---------------------------------------------------------------------------
# 4. Route guards — unauthenticated access
# ---------------------------------------------------------------------------

class TestRouteGuards:
    def test_dashboard_without_session_redirects(self, client):
        resp = client.get("/dashboard", follow_redirects=False)
        assert resp.status_code == 302
        assert "/login" in resp.headers["Location"]

    def test_deposit_without_session_redirects(self, client):
        resp = client.get("/deposit", follow_redirects=False)
        assert resp.status_code == 302
        assert "/login" in resp.headers["Location"]

    def test_withdraw_without_session_redirects(self, client):
        resp = client.get("/withdraw", follow_redirects=False)
        assert resp.status_code == 302
        assert "/login" in resp.headers["Location"]

    def test_logout_without_session_redirects(self, client):
        resp = client.get("/logout", follow_redirects=False)
        assert resp.status_code == 302
        assert "/login" in resp.headers["Location"]


# ---------------------------------------------------------------------------
# 5. Dashboard
# ---------------------------------------------------------------------------

class TestDashboard:
    def test_dashboard_shows_customer_name(self, client):
        _login(client)
        resp = client.get("/dashboard", follow_redirects=True)
        assert resp.status_code == 200
        assert b"Alice Johnson" in resp.data

    def test_dashboard_shows_balance(self, client):
        _login(client)
        resp = client.get("/dashboard", follow_redirects=True)
        # Balance shown as currency value
        assert b"5000.00" in resp.data or b"5,000.00" in resp.data


# ---------------------------------------------------------------------------
# 6. Deposit
# ---------------------------------------------------------------------------

class TestDeposit:
    def test_get_deposit_page_200(self, client):
        _login(client)
        resp = client.get("/deposit", follow_redirects=True)
        assert resp.status_code == 200

    def test_valid_deposit_redirects_to_dashboard(self, client):
        _login(client)
        resp = client.post(
            "/deposit", data={"amount": "500"}, follow_redirects=False
        )
        assert resp.status_code == 302
        assert "/dashboard" in resp.headers["Location"]

    def test_deposit_increases_balance(self, client):
        _login(client)
        client.post("/deposit", data={"amount": "500"}, follow_redirects=False)
        resp = client.get("/dashboard", follow_redirects=True)
        # Alice starts at 5000, should now show 5500
        assert b"5500.00" in resp.data or b"5,500.00" in resp.data

    def test_empty_deposit_amount_shows_error(self, client):
        _login(client)
        resp = client.post("/deposit", data={"amount": ""})
        assert resp.status_code == 200
        assert b"Please enter" in resp.data

    def test_non_numeric_deposit_shows_error(self, client):
        _login(client)
        resp = client.post("/deposit", data={"amount": "abc"})
        assert resp.status_code == 200
        assert b"valid number" in resp.data

    def test_zero_deposit_shows_error(self, client):
        _login(client)
        resp = client.post("/deposit", data={"amount": "0"})
        assert resp.status_code == 200
        assert b"greater than zero" in resp.data

    def test_negative_deposit_shows_error(self, client):
        _login(client)
        resp = client.post("/deposit", data={"amount": "-100"})
        assert resp.status_code == 200
        assert b"greater than zero" in resp.data


# ---------------------------------------------------------------------------
# 7. Withdrawal
# ---------------------------------------------------------------------------

class TestWithdraw:
    def test_get_withdraw_page_200(self, client):
        _login(client)
        resp = client.get("/withdraw", follow_redirects=True)
        assert resp.status_code == 200

    def test_valid_withdrawal_redirects_to_dashboard(self, client):
        _login(client)
        resp = client.post(
            "/withdraw", data={"amount": "100"}, follow_redirects=False
        )
        assert resp.status_code == 302
        assert "/dashboard" in resp.headers["Location"]

    def test_withdrawal_decreases_balance(self, client):
        _login(client)
        client.post("/withdraw", data={"amount": "1000"}, follow_redirects=False)
        resp = client.get("/dashboard", follow_redirects=True)
        # Alice starts at 5000, should now show 4000
        assert b"4000.00" in resp.data or b"4,000.00" in resp.data

    def test_insufficient_funds_shows_error(self, client):
        _login(client, username="charlie", password="password123")
        # Charlie has 750.00 — try to withdraw 1000
        resp = client.post("/withdraw", data={"amount": "1000"})
        assert resp.status_code == 200
        assert b"Insufficient funds" in resp.data

    def test_balance_unchanged_after_failed_withdrawal(self, client):
        _login(client, username="charlie", password="password123")
        client.post("/withdraw", data={"amount": "9999"})
        resp = client.get("/dashboard", follow_redirects=True)
        assert b"750.00" in resp.data

    def test_empty_withdrawal_shows_error(self, client):
        _login(client)
        resp = client.post("/withdraw", data={"amount": ""})
        assert resp.status_code == 200
        assert b"Please enter" in resp.data


# ---------------------------------------------------------------------------
# 8. Logout
# ---------------------------------------------------------------------------

class TestLogout:
    def test_logout_redirects_to_login(self, client):
        _login(client)
        resp = client.get("/logout", follow_redirects=False)
        assert resp.status_code == 302
        assert "/login" in resp.headers["Location"]

    def test_dashboard_inaccessible_after_logout(self, client):
        _login(client)
        client.get("/logout", follow_redirects=True)
        resp = client.get("/dashboard", follow_redirects=False)
        assert resp.status_code == 302
        assert "/login" in resp.headers["Location"]


# ---------------------------------------------------------------------------
# 9. Error pages
# ---------------------------------------------------------------------------

class TestErrorPages:
    def test_404_returns_404_status(self, client):
        resp = client.get("/this-page-does-not-exist")
        assert resp.status_code == 404
