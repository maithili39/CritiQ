"""
Regression tests for the exact vulnerability the user-scoped auth work fixed:
a session_id alone must never be enough to read or mutate someone else's interview.
"""

from tests.conftest import make_session


def _register(client, email="a@example.com", password="longenough1"):
    res = client.post("/api/auth/register", json={"email": email, "password": password})
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def test_owner_can_create_and_read_own_session(client, mock_ai):
    headers = _register(client)
    session_id = make_session(client, headers, mock_ai)

    res = client.get(f"/api/sessions/{session_id}", headers=headers)
    assert res.status_code == 200
    assert res.json()["id"] == session_id


def test_other_user_cannot_read_session(client, mock_ai):
    owner_headers = _register(client, "owner@example.com")
    attacker_headers = _register(client, "attacker@example.com")

    session_id = make_session(client, owner_headers, mock_ai)

    res = client.get(f"/api/sessions/{session_id}", headers=attacker_headers)
    assert res.status_code == 404  # not 403 — must not reveal the session exists


def test_other_user_cannot_start_session(client, mock_ai):
    owner_headers = _register(client, "owner2@example.com")
    attacker_headers = _register(client, "attacker2@example.com")

    session_id = make_session(client, owner_headers, mock_ai)

    res = client.post(f"/api/sessions/{session_id}/start", headers=attacker_headers)
    assert res.status_code == 404


def test_other_user_cannot_submit_answer(client, mock_ai):
    owner_headers = _register(client, "owner3@example.com")
    attacker_headers = _register(client, "attacker3@example.com")

    session_id = make_session(client, owner_headers, mock_ai)
    client.post(f"/api/sessions/{session_id}/start", headers=owner_headers)

    res = client.post(
        f"/api/sessions/{session_id}/answers?question_id=nonexistent",
        json={"answer_text": "an answer"},
        headers=attacker_headers,
    )
    assert res.status_code == 404


def test_unauthenticated_request_is_rejected(client, mock_ai):
    owner_headers = _register(client, "owner4@example.com")
    session_id = make_session(client, owner_headers, mock_ai)

    res = client.get(f"/api/sessions/{session_id}")
    assert res.status_code in (401, 422)


def test_list_sessions_only_returns_own(client, mock_ai):
    headers_a = _register(client, "list-a@example.com")
    headers_b = _register(client, "list-b@example.com")

    session_a = make_session(client, headers_a, mock_ai, candidate_name="Candidate A")
    make_session(client, headers_b, mock_ai, candidate_name="Candidate B")

    res = client.get("/api/sessions", headers=headers_a)
    assert res.status_code == 200
    sessions = res.json()["sessions"]
    assert [s["id"] for s in sessions] == [session_a]
    assert sessions[0]["candidate_name"] == "Candidate A"
