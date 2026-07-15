"""Unit tests for score↔outcome calibration math (deterministic, no LLM)."""

import pytest

from app.core.rubrics import get_rubric, weighted_score
from app.services.interview_orchestrator import _pearson


def test_weighted_score_is_deterministic_weighted_sum():
    rubric = get_rubric("ai_ml")
    # All dimensions max → 10; all zero → 0.
    assert weighted_score({d["key"]: 10 for d in rubric}, rubric) == 10.0
    assert weighted_score({d["key"]: 0 for d in rubric}, rubric) == 0.0


def test_weighted_score_respects_weights():
    rubric = get_rubric("ai_ml")  # correctness weight 0.4 dominates
    high_correctness = weighted_score(
        {"correctness": 10, "depth": 0, "applied_reasoning": 0, "communication": 0}, rubric
    )
    high_communication = weighted_score(
        {"correctness": 0, "depth": 0, "applied_reasoning": 0, "communication": 10}, rubric
    )
    assert high_correctness > high_communication


def test_custom_role_falls_back_to_default_rubric():
    rubric = get_rubric("some_unknown_custom_role")
    assert {d["key"] for d in rubric} == {"correctness", "depth", "communication"}


def test_pearson_perfect_positive():
    assert _pearson([1, 2, 3], [2, 4, 6]) == pytest.approx(1.0)


def test_pearson_perfect_negative():
    assert _pearson([1, 2, 3], [6, 4, 2]) == pytest.approx(-1.0)


def test_pearson_zero_variance_returns_none():
    assert _pearson([5, 5, 5], [1, 2, 3]) is None


def test_pearson_empty_returns_none():
    assert _pearson([], []) is None
