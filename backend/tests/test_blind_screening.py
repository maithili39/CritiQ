"""Unit tests for demographic-blind resume redaction (deterministic, no LLM)."""

from app.services.resume_parser import redact_pii


def test_redacts_email():
    out = redact_pii("Contact: jane.doe@example.com for details")
    assert "jane.doe@example.com" not in out
    assert "[REDACTED]" in out


def test_redacts_phone_number():
    out = redact_pii("Phone: +1 (415) 555-2671")
    assert "555" not in out
    assert "[REDACTED]" in out


def test_redacts_urls_and_profiles():
    out = redact_pii("Portfolio https://github.com/janedoe and www.linkedin.com/in/jane")
    assert "github.com/janedoe" not in out
    assert "linkedin.com/in/jane" not in out


def test_redacts_explicit_demographic_lines():
    text = "Gender: Female\nDate of Birth: 12/03/1997\nNationality: Indian"
    out = redact_pii(text)
    assert "Female" not in out
    assert "1997" not in out
    assert "Indian" not in out


def test_preserves_skills_and_experience():
    text = "Skills: Python, PyTorch, distributed systems. 5 years building ML pipelines."
    out = redact_pii(text)
    # Substance the evaluation depends on must survive redaction untouched.
    assert "Python" in out
    assert "PyTorch" in out
    assert "5 years building ML pipelines" in out


def test_email_digits_not_left_as_phone():
    # An email removed first must not leave a trailing digit fragment to be re-matched.
    out = redact_pii("reach me: user2024@mail.com")
    assert "2024" not in out
