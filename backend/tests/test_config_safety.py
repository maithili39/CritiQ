"""
Unit tests for startup safety checks in app/core/config.py - guards against
config mistakes that would silently weaken security rather than fail loudly.
"""

import pytest

from app.core.config import validate_cors_origins


def test_wildcard_origin_raises_when_not_debug():
    with pytest.raises(RuntimeError, match="ALLOWED_ORIGINS"):
        validate_cors_origins(["*"], debug=False)


def test_wildcard_origin_only_warns_in_debug():
    # Should not raise - DEBUG mode is for local dev, where this is a lesser concern.
    validate_cors_origins(["*"], debug=True)


def test_specific_origins_are_fine():
    validate_cors_origins(["https://critiq.vercel.app"], debug=False)
    validate_cors_origins(["http://localhost:3000", "https://critiq.vercel.app"], debug=False)


def test_empty_origins_list_is_fine():
    validate_cors_origins([], debug=False)
