from fastapi.testclient import TestClient

import app as app_module

client = TestClient(app_module.app, follow_redirects=False)

PAYLOAD = {
    "name": "Test User",
    "address": "Gwalior 474001",
    "ivrs": "n2253012669",
    "meter_type": "Single-phase",
    "roof_area_sqft": 500,
    "months": [{"kwh": 148, "bill": 1628}, {"kwh": 90, "bill": 990}, {"kwh": 52, "bill": 572}],
}


def login(c, password="pass123"):
    return c.post("/login", data={"username": "tester", "password": password})


def test_pages_require_login():
    assert client.get("/").status_code == 303
    assert client.post("/api/generate", json=PAYLOAD).status_code == 401


def test_login_and_generate_pdf():
    c = TestClient(app_module.app, follow_redirects=False)
    assert login(c).headers["location"] == "/"
    assert c.get("/").status_code == 200
    res = c.post("/api/generate", json=PAYLOAD)
    assert res.status_code == 200
    assert res.content.startswith(b"%PDF")
    assert "N2253012669_mini_report.pdf" in res.headers["content-disposition"]


def test_bad_input_rejected():
    c = TestClient(app_module.app, follow_redirects=False)
    login(c)
    bad = {**PAYLOAD, "ivrs": "12", "months": []}
    assert c.post("/api/generate", json=bad).status_code == 422


def test_lockout_after_repeated_failures(monkeypatch):
    monkeypatch.setattr(app_module.time, "sleep", lambda s: None)
    app_module._failures.clear()
    c = TestClient(app_module.app, follow_redirects=False)
    for _ in range(app_module.MAX_FAILS_PER_IP):
        assert login(c, "wrong").headers["location"] == "/login?error=1"
    # now even the correct password is refused
    assert login(c).headers["location"] == "/login?error=2"
    app_module._failures.clear()
