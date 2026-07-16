"""
Admin endpoints: API-key gating, knowledge-base ingestion/status (with the
ChromaDB-backed pipeline faked), and the custom-role registry CRUD.
"""

import json

import pytest

import app.api.admin as admin_module
from app.core.config import settings

ADMIN_HEADERS = {"X-Admin-API-Key": "the-real-key"}


@pytest.fixture()
def admin_client(client, monkeypatch):
    monkeypatch.setattr(settings, "ADMIN_API_KEY", "the-real-key")
    return client


# --- API-key gating ---


def test_admin_disabled_when_no_key_configured(client, monkeypatch):
    monkeypatch.setattr(settings, "ADMIN_API_KEY", "")
    res = client.get("/api/admin/knowledge-base/status")
    assert res.status_code == 503


def test_admin_rejects_missing_key(admin_client):
    res = admin_client.get("/api/admin/knowledge-base/status")
    assert res.status_code in (401, 403, 422)


def test_admin_rejects_wrong_key(admin_client):
    res = admin_client.get("/api/admin/knowledge-base/status", headers={"X-Admin-API-Key": "wrong"})
    assert res.status_code == 403


def test_admin_accepts_correct_key(admin_client, monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "CHROMA_PERSIST_DIR", str(tmp_path / "chroma"))  # don't touch real data dir
    res = admin_client.get("/api/admin/knowledge-base/status", headers=ADMIN_HEADERS)
    assert res.status_code == 200


# --- Knowledge-base ingestion (pipeline faked; endpoint logic under test) ---


def test_ingest_unknown_role_is_rejected(admin_client):
    res = admin_client.post("/api/admin/ingest/not_a_role", headers=ADMIN_HEADERS)
    assert res.status_code == 400
    assert "ai_ml" in res.json()["detail"]  # error names the valid slugs


def test_ingest_single_role_reports_chunk_count(admin_client, monkeypatch):
    calls = []

    def fake_ingest(role, force_reingest=False):
        calls.append((role, force_reingest))
        return 42

    monkeypatch.setattr(admin_module, "ingest_role_documents", fake_ingest)
    res = admin_client.post("/api/admin/ingest/ai_ml?force=true", headers=ADMIN_HEADERS)
    assert res.status_code == 200
    assert res.json()["results"]["ai_ml"] == {"status": "ok", "chunks": 42}
    assert calls == [("ai_ml", True)]


def test_ingest_all_covers_every_builtin_role(admin_client, monkeypatch):
    monkeypatch.setattr(admin_module, "ingest_role_documents", lambda role, force_reingest=False: 7)
    res = admin_client.post("/api/admin/ingest/all", headers=ADMIN_HEADERS)
    assert res.status_code == 200
    assert set(res.json()["results"].keys()) == set(admin_module.ROLES)


def test_ingest_failure_is_reported_per_role_not_500(admin_client, monkeypatch):
    def boom(role, force_reingest=False):
        raise RuntimeError("chroma unavailable")

    monkeypatch.setattr(admin_module, "ingest_role_documents", boom)
    res = admin_client.post("/api/admin/ingest/ai_ml", headers=ADMIN_HEADERS)
    assert res.status_code == 200  # partial-failure result, not a crashed request
    assert res.json()["results"]["ai_ml"]["status"] == "error"
    assert "chroma unavailable" in res.json()["results"]["ai_ml"]["error"]


def test_knowledge_base_status_reports_ready_and_error_roles(admin_client, monkeypatch):
    class FakeCollection:
        def __init__(self, n):
            self._n = n

        def count(self):
            return self._n

    def fake_get_collection(slug):
        if slug == "ai_ml":
            return FakeCollection(120)
        raise RuntimeError("collection missing")

    monkeypatch.setattr(admin_module, "get_collection", fake_get_collection)
    res = admin_client.get("/api/admin/knowledge-base/status", headers=ADMIN_HEADERS)
    assert res.status_code == 200
    body = res.json()
    assert body["ai_ml"]["status"] == "ready" and body["ai_ml"]["chunks"] == 120
    assert body["data_science"]["status"] == "error"


# --- Custom role registry ---

_ROLE_PAYLOAD = {
    "slug": "devops_eng",
    "label": "DevOps Engineer",
    "description": "CI/CD and infra",
    "topics": ["kubernetes", "terraform"],
}


def test_create_custom_role_generates_profile_when_not_supplied(admin_client, monkeypatch):
    generated = {
        "persona": "You are a staff DevOps engineer conducting a technical screening interview.",
        "difficulty_guide": {"junior": "j", "mid": "m", "senior": "s"},
    }
    monkeypatch.setattr(admin_module, "generate_role_profile", lambda *a, **k: generated)

    res = admin_client.post("/api/admin/roles", json=_ROLE_PAYLOAD, headers=ADMIN_HEADERS)
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["slug"] == "devops_eng"
    assert body["persona"] == generated["persona"]


def test_create_custom_role_uses_supplied_profile_without_llm(admin_client, monkeypatch):
    def must_not_be_called(*_a, **_k):
        raise AssertionError("generate_role_profile must not run when a full profile is supplied")

    monkeypatch.setattr(admin_module, "generate_role_profile", must_not_be_called)
    payload = {**_ROLE_PAYLOAD, "persona": "You are an SRE lead.", "difficulty_guide": json.dumps({"mid": "m"})}
    res = admin_client.post("/api/admin/roles", json=payload, headers=ADMIN_HEADERS)
    assert res.status_code == 201, res.text
    assert res.json()["persona"] == "You are an SRE lead."


def test_create_custom_role_rejects_builtin_slug_collision(admin_client):
    res = admin_client.post("/api/admin/roles", json={**_ROLE_PAYLOAD, "slug": "ai_ml"}, headers=ADMIN_HEADERS)
    assert res.status_code == 409


def test_create_custom_role_rejects_duplicate_custom_slug(admin_client, monkeypatch):
    monkeypatch.setattr(
        admin_module, "generate_role_profile", lambda *a, **k: {"persona": "p", "difficulty_guide": {}}
    )
    first = admin_client.post("/api/admin/roles", json=_ROLE_PAYLOAD, headers=ADMIN_HEADERS)
    assert first.status_code == 201
    dup = admin_client.post("/api/admin/roles", json=_ROLE_PAYLOAD, headers=ADMIN_HEADERS)
    assert dup.status_code == 409


def test_list_roles_includes_builtin_and_custom(admin_client, monkeypatch):
    monkeypatch.setattr(
        admin_module, "generate_role_profile", lambda *a, **k: {"persona": "p", "difficulty_guide": {}}
    )
    admin_client.post("/api/admin/roles", json=_ROLE_PAYLOAD, headers=ADMIN_HEADERS)
    res = admin_client.get("/api/admin/roles", headers=ADMIN_HEADERS)
    slugs = {r["slug"] for r in res.json()["roles"]}
    assert {"ai_ml", "data_science", "devops_eng"} <= slugs


def test_delete_builtin_role_is_forbidden(admin_client):
    res = admin_client.delete("/api/admin/roles/ai_ml", headers=ADMIN_HEADERS)
    assert res.status_code == 400


def test_delete_missing_custom_role_404(admin_client):
    res = admin_client.delete("/api/admin/roles/ghost_role", headers=ADMIN_HEADERS)
    assert res.status_code == 404


def test_delete_custom_role_succeeds(admin_client, monkeypatch):
    monkeypatch.setattr(
        admin_module, "generate_role_profile", lambda *a, **k: {"persona": "p", "difficulty_guide": {}}
    )
    admin_client.post("/api/admin/roles", json=_ROLE_PAYLOAD, headers=ADMIN_HEADERS)
    res = admin_client.delete("/api/admin/roles/devops_eng", headers=ADMIN_HEADERS)
    assert res.status_code == 200
    # gone from the registry afterwards
    slugs = {r["slug"] for r in admin_client.get("/api/admin/roles", headers=ADMIN_HEADERS).json()["roles"]}
    assert "devops_eng" not in slugs
