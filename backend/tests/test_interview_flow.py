"""End-to-end happy-path test: create -> start -> answer through to completion -> report."""

from tests.conftest import make_session


def _register(client, email="flow@example.com", password="longenough1"):
    res = client.post("/api/auth/register", json={"email": email, "password": password})
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def test_full_interview_flow_reaches_report(client, mock_ai):
    from app.core.config import settings

    headers = _register(client)
    session_id = make_session(client, headers, mock_ai)

    started = client.post(f"/api/sessions/{session_id}/start", headers=headers)
    assert started.status_code == 200
    question = started.json()["question"]
    assert question["order"] == 1

    is_complete = False
    for _ in range(settings.MAX_QUESTIONS):
        res = client.post(
            f"/api/sessions/{session_id}/answers?question_id={question['id']}",
            json={"answer_text": "A thorough, well-reasoned answer."},
            headers=headers,
        )
        assert res.status_code == 200
        body = res.json()
        assert body["score"] == 8.0
        is_complete = body["is_complete"]
        if is_complete:
            break
        question = body["next_question"]

    assert is_complete

    completed = client.post(f"/api/sessions/{session_id}/complete", headers=headers)
    assert completed.status_code == 200
    report = completed.json()["report"]
    assert report["recommendation"] == "yes"
    assert report["overall_score"] == 8.0

    full = client.get(f"/api/sessions/{session_id}", headers=headers)
    assert full.status_code == 200
    assert full.json()["status"] == "completed"
    assert full.json()["report"]["recommendation"] == "yes"


def test_answer_is_rejected_when_empty(client, mock_ai):
    headers = _register(client, "empty-answer@example.com")
    session_id = make_session(client, headers, mock_ai)
    started = client.post(f"/api/sessions/{session_id}/start", headers=headers)
    question_id = started.json()["question"]["id"]

    res = client.post(
        f"/api/sessions/{session_id}/answers?question_id={question_id}",
        json={"answer_text": "   "},
        headers=headers,
    )
    assert res.status_code == 400


def test_report_unavailable_before_complete(client, mock_ai):
    headers = _register(client, "no-report-yet@example.com")
    session_id = make_session(client, headers, mock_ai)
    client.post(f"/api/sessions/{session_id}/start", headers=headers)

    res = client.get(f"/api/sessions/{session_id}/report", headers=headers)
    assert res.status_code == 400


def test_create_session_rejects_non_pdf(client, mock_ai):
    headers = _register(client, "bad-file@example.com")
    files = {"resume": ("resume.txt", b"just some text", "text/plain")}
    data = {"candidate_name": "Someone", "role": "ai_ml"}
    res = client.post("/api/sessions", data=data, files=files, headers=headers)
    assert res.status_code == 400


def test_create_session_rejects_fake_pdf_extension(client, mock_ai):
    """A .pdf filename with non-PDF content must be rejected by the magic-byte check."""
    headers = _register(client, "fake-pdf@example.com")
    files = {"resume": ("resume.pdf", b"not actually a pdf", "application/pdf")}
    data = {"candidate_name": "Someone", "role": "ai_ml"}
    res = client.post("/api/sessions", data=data, files=files, headers=headers)
    assert res.status_code == 400


def test_create_session_rejects_invalid_role(client, mock_ai):
    headers = _register(client, "bad-role@example.com")
    files = {"resume": ("resume.pdf", b"%PDF-1.4 mock", "application/pdf")}
    data = {"candidate_name": "Someone", "role": "backend_engineer"}
    res = client.post("/api/sessions", data=data, files=files, headers=headers)
    assert res.status_code == 400
