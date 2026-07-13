"""
Tests for the token-authenticated candidate interview flow (/api/candidate/sessions/*):
the invite link a recruiter sends a candidate, requiring no account.
"""

from tests.conftest import make_session


def _register(client, email="recruiter@example.com", password="longenough1"):
    res = client.post("/api/auth/register", json={"email": email, "password": password})
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def _create_with_invite(client, headers, mock_ai, **kwargs):
    """Creates a session and returns (session_id, invite_token)."""
    session_id = make_session(client, headers, mock_ai, **kwargs)
    res = client.get(f"/api/sessions/{session_id}", headers=headers)
    assert res.status_code == 200
    invite_url = res.json()["invite_url"]
    token = invite_url.split("token=")[1]
    return session_id, token


def test_create_session_returns_invite_url(client, mock_ai):
    headers = _register(client)
    files = {"resume": ("resume.pdf", b"%PDF-1.4 mock", "application/pdf")}
    data = {"candidate_name": "Ada Lovelace", "role": "ai_ml"}
    res = client.post("/api/sessions", data=data, files=files, headers=headers)
    assert res.status_code == 200
    assert "token=" in res.json()["invite_url"]


def test_candidate_can_complete_full_flow_with_token_only(client, mock_ai):
    from app.core.config import settings

    headers = _register(client, "recruiter2@example.com")
    session_id, token = _create_with_invite(client, headers, mock_ai)

    started = client.post(f"/api/candidate/sessions/{session_id}/start?token={token}")
    assert started.status_code == 200
    question = started.json()["question"]
    assert question["order"] == 1

    is_complete = False
    for _ in range(settings.MAX_QUESTIONS):
        res = client.post(
            f"/api/candidate/sessions/{session_id}/answers?token={token}&question_id={question['id']}",
            json={"answer_text": "A thorough, well-reasoned answer."},
        )
        assert res.status_code == 200
        body = res.json()
        # Candidate must never see a score or rationale in the answer response.
        assert "score" not in body
        assert "rationale" not in body
        is_complete = body["is_complete"]
        if is_complete:
            break
        question = body["next_question"]

    assert is_complete

    completed = client.post(f"/api/candidate/sessions/{session_id}/complete?token={token}")
    assert completed.status_code == 200
    # Candidate confirmation must never include the report/recommendation.
    assert "report" not in completed.json()
    assert "recommendation" not in completed.json()

    # Recruiter, meanwhile, sees the full report.
    full = client.get(f"/api/sessions/{session_id}", headers=headers)
    assert full.json()["report"]["recommendation"] == "yes"


def test_wrong_token_is_rejected(client, mock_ai):
    headers = _register(client, "recruiter3@example.com")
    session_id, _real_token = _create_with_invite(client, headers, mock_ai)

    res = client.get(f"/api/candidate/sessions/{session_id}?token=not-the-real-token")
    assert res.status_code == 404


def test_missing_token_is_rejected(client, mock_ai):
    headers = _register(client, "recruiter4@example.com")
    session_id, _token = _create_with_invite(client, headers, mock_ai)

    res = client.get(f"/api/candidate/sessions/{session_id}")
    assert res.status_code == 422  # required query param missing


def test_candidate_cannot_start_session_twice(client, mock_ai):
    headers = _register(client, "recruiter5@example.com")
    session_id, token = _create_with_invite(client, headers, mock_ai)

    first = client.post(f"/api/candidate/sessions/{session_id}/start?token={token}")
    assert first.status_code == 200

    second = client.post(f"/api/candidate/sessions/{session_id}/start?token={token}")
    assert second.status_code == 409


def test_recruiter_start_after_candidate_start_is_rejected(client, mock_ai):
    """Guards against a race: recruiter previewing after the candidate already began."""
    headers = _register(client, "recruiter6@example.com")
    session_id, token = _create_with_invite(client, headers, mock_ai)

    client.post(f"/api/candidate/sessions/{session_id}/start?token={token}")

    res = client.post(f"/api/sessions/{session_id}/start", headers=headers)
    assert res.status_code == 409


def test_resend_invite_requires_candidate_email(client, mock_ai):
    headers = _register(client, "recruiter7@example.com")
    session_id = make_session(client, headers, mock_ai)  # no candidate_email passed

    res = client.post(f"/api/sessions/{session_id}/invite/send", headers=headers)
    assert res.status_code == 400
