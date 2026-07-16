"""Unit tests for the SMTP emailer: unconfigured fallback, happy path, and send failure."""

from unittest.mock import MagicMock

import pytest

import app.services.emailer as emailer


@pytest.fixture()
def smtp_configured(monkeypatch):
    monkeypatch.setattr(emailer.settings, "SMTP_HOST", "smtp.test")
    monkeypatch.setattr(emailer.settings, "SMTP_PORT", 587)
    monkeypatch.setattr(emailer.settings, "SMTP_USERNAME", "user")
    monkeypatch.setattr(emailer.settings, "SMTP_PASSWORD", "pass")
    monkeypatch.setattr(emailer.settings, "SMTP_USE_TLS", True)
    monkeypatch.setattr(emailer.settings, "EMAIL_FROM", "noreply@test")


def test_unconfigured_smtp_returns_false_without_network(monkeypatch):
    monkeypatch.setattr(emailer.settings, "SMTP_HOST", "")

    def explode(*_a, **_k):  # any SMTP attempt would be a bug
        raise AssertionError("SMTP must not be contacted when unconfigured")

    monkeypatch.setattr(emailer.smtplib, "SMTP", explode)
    assert emailer.send_text_email("a@b.c", "subj", "body") is False


def test_sends_email_with_tls_and_login(smtp_configured, monkeypatch):
    server = MagicMock()
    smtp_ctx = MagicMock()
    smtp_ctx.__enter__.return_value = server
    smtp_cls = MagicMock(return_value=smtp_ctx)
    monkeypatch.setattr(emailer.smtplib, "SMTP", smtp_cls)

    assert emailer.send_text_email("a@b.c", "Reset your password", "click here") is True
    smtp_cls.assert_called_once_with("smtp.test", 587, timeout=15)
    server.starttls.assert_called_once()
    server.login.assert_called_once_with("user", "pass")
    msg = server.send_message.call_args[0][0]
    assert msg["To"] == "a@b.c"
    assert msg["From"] == "noreply@test"
    assert msg["Subject"] == "Reset your password"


def test_smtp_failure_returns_false_not_raise(smtp_configured, monkeypatch):
    def boom(*_a, **_k):
        raise ConnectionRefusedError("no route")

    monkeypatch.setattr(emailer.smtplib, "SMTP", boom)
    # Auth flows treat email as best-effort; a mail outage must not 500 the request.
    assert emailer.send_text_email("a@b.c", "subj", "body") is False
