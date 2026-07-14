"""
Load test simulating concurrent full interviews end to end: register, create a
session (real PDF upload + real Claude resume parsing), start it, answer every
question, complete it, and check the report.

This hits a REAL backend with REAL Claude API calls - it costs real API usage
and should only be pointed at a staging/test environment you control, never at
data you can't afford to spam.

Usage:
    pip install -r requirements-dev.txt
    locust -f scripts/locustfile.py --host https://your-staging-backend.example.com

Then open http://localhost:8089, set concurrent users + spawn rate, and start.
Watch for: response time percentiles climbing, error rate rising, and (in the
backend's own logs) the per-Claude-call timing added in app/services/llm.py to
see which stage of the interview degrades first under load.
"""

import io
import random
import uuid

from locust import HttpUser, between, task

# A tiny valid PDF (just the magic bytes + minimal structure) so the backend's
# PDF validation passes without needing a real resume file checked into the repo.
_MINIMAL_PDF = (
    b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
    b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]>>endobj\n"
    b"xref\n0 4\ntrailer<</Size 4/Root 1 0 R>>\n%%EOF"
)


class InterviewUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        email = f"loadtest-{uuid.uuid4().hex[:12]}@example.com"
        res = self.client.post(
            "/api/auth/register",
            json={"email": email, "password": "longenough-password-1"},
            name="/auth/register",
        )
        self.token = res.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}

    @task
    def full_interview(self):
        role = random.choice(["ai_ml", "data_science"])

        create_res = self.client.post(
            "/api/sessions",
            data={"candidate_name": "Load Test Candidate", "role": role},
            files={"resume": ("resume.pdf", io.BytesIO(_MINIMAL_PDF), "application/pdf")},
            headers=self.headers,
            name="/sessions [create]",
        )
        if create_res.status_code != 200:
            return
        session_id = create_res.json()["session_id"]

        start_res = self.client.post(
            f"/api/sessions/{session_id}/start",
            headers=self.headers,
            name="/sessions/:id/start",
        )
        if start_res.status_code != 200:
            return
        question = start_res.json()["question"]

        for _ in range(8):  # MAX_QUESTIONS default
            answer_res = self.client.post(
                f"/api/sessions/{session_id}/answers?question_id={question['id']}",
                json={"answer_text": "A thorough, well-reasoned answer covering the key trade-offs."},
                headers=self.headers,
                name="/sessions/:id/answers",
            )
            if answer_res.status_code != 200:
                return
            body = answer_res.json()
            if body["is_complete"] or not body.get("next_question"):
                break
            question = body["next_question"]

        self.client.post(
            f"/api/sessions/{session_id}/complete",
            headers=self.headers,
            name="/sessions/:id/complete",
        )
