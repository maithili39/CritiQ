"""Admin endpoints must require a valid X-Admin-API-Key header."""

from app.core.config import settings


def test_admin_disabled_when_no_key_configured(client, monkeypatch):
    monkeypatch.setattr(settings, "ADMIN_API_KEY", "")
    res = client.get("/api/admin/knowledge-base/status")
    assert res.status_code == 503


def test_admin_rejects_missing_key(client, monkeypatch):
    monkeypatch.setattr(settings, "ADMIN_API_KEY", "the-real-key")
    res = client.get("/api/admin/knowledge-base/status")
    assert res.status_code in (401, 403, 422)


def test_admin_rejects_wrong_key(client, monkeypatch):
    monkeypatch.setattr(settings, "ADMIN_API_KEY", "the-real-key")
    res = client.get("/api/admin/knowledge-base/status", headers={"X-Admin-API-Key": "wrong"})
    assert res.status_code == 403


def test_admin_accepts_correct_key(client, monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "ADMIN_API_KEY", "the-real-key")
    monkeypatch.setattr(settings, "CHROMA_PERSIST_DIR", str(tmp_path / "chroma"))  # don't touch real data dir
    res = client.get("/api/admin/knowledge-base/status", headers={"X-Admin-API-Key": "the-real-key"})
    assert res.status_code == 200
