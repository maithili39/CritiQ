"""
Unit tests for question generation, rubric evaluation, and report generation —
the LLM-facing core of the product. `call_tool` and the retriever are mocked so
these run offline; what's under test is prompt construction, result enrichment,
weighted-score math, consistency checking, and failure behavior (propagate vs.
fallback).
"""

import pytest

import app.services.question_generator as qg
from app.core.rubrics import get_rubric, weighted_score

_RETRIEVAL = {
    "experience_level": "senior",
    "query_skills": ["PyTorch", "NLP"],
    "context_text": "Gradient descent minimizes a loss function iteratively. " * 40,
    "sources": [{"file": "mml_book.pdf", "page": 12}],
}


@pytest.fixture()
def captured_calls(monkeypatch):
    """Mocks the retriever and call_tool; records every call_tool kwargs."""
    calls: list[dict] = []

    def fake_retrieve(**_kwargs):
        return dict(_RETRIEVAL)

    def fake_call_tool(**kwargs):
        calls.append(kwargs)
        return {"text": "What is overfitting?", "topic": "Overfitting", "rationale": "matches profile"}

    monkeypatch.setattr(qg, "retrieve_for_question_generation", fake_retrieve)
    monkeypatch.setattr(qg, "call_tool", fake_call_tool)
    return calls


# --- generate_question ---


def test_generate_question_enriches_result(captured_calls):
    result = qg.generate_question(role="ai_ml", parsed_resume={"summary": "ML eng"}, previous_questions=[])
    assert result["text"] == "What is overfitting?"
    assert result["difficulty"] == "senior"  # from retrieval, not the model
    assert result["question_type"] == "conceptual"  # question 1
    assert result["source_context"] == _RETRIEVAL["context_text"][:1500]
    assert result["sources"] == _RETRIEVAL["sources"]


def test_question_type_cycles_through_all_five(captured_calls):
    types = [
        qg.generate_question(role="ai_ml", parsed_resume={}, previous_questions=[], question_number=n)["question_type"]
        for n in range(1, 7)
    ]
    assert types == ["conceptual", "applied", "scenario", "debugging", "design", "conceptual"]


def test_role_profile_persona_is_used_in_system_prompt(captured_calls):
    profile = {"persona": "You are a principal robotics engineer.", "difficulty": "Probe kinematics edge cases."}
    qg.generate_question(role="robotics", parsed_resume={}, previous_questions=[], role_profile=profile)
    system = captured_calls[-1]["system"]
    assert "principal robotics engineer" in system
    assert "Probe kinematics edge cases." in system


def test_generic_persona_fallback_without_role_profile(captured_calls):
    qg.generate_question(role="ai_ml", parsed_resume={}, previous_questions=[])
    assert "senior engineer conducting a technical interview" in captured_calls[-1]["system"]


def test_only_last_three_previous_questions_in_prompt(captured_calls):
    prev = [f"Question {i}" for i in range(1, 6)]  # Q1..Q5
    qg.generate_question(role="ai_ml", parsed_resume={}, previous_questions=prev, question_number=6)
    user = captured_calls[-1]["user_content"]
    assert "Question 5" in user and "Question 3" in user
    assert "Question 1" not in user and "Question 2" not in user


def test_adaptive_text_included_only_after_first_question(captured_calls):
    qg.generate_question(
        role="ai_ml",
        parsed_resume={},
        previous_questions=["Q1"],
        previous_answer="SGD uses minibatches...",
        question_number=2,
    )
    assert "SGD uses minibatches" in captured_calls[-1]["user_content"]

    qg.generate_question(
        role="ai_ml", parsed_resume={}, previous_questions=[], previous_answer="ignored", question_number=1
    )
    assert "ignored" not in captured_calls[-1]["user_content"]


def test_generate_question_propagates_llm_failure(monkeypatch):
    # Policy: no fake placeholder question may reach a candidate — errors surface.
    monkeypatch.setattr(qg, "retrieve_for_question_generation", lambda **_: dict(_RETRIEVAL))

    def boom(**_kwargs):
        raise RuntimeError("provider down")

    monkeypatch.setattr(qg, "call_tool", boom)
    with pytest.raises(RuntimeError, match="provider down"):
        qg.generate_question(role="ai_ml", parsed_resume={}, previous_questions=[])


# --- evaluate_answer ---


def test_evaluate_answer_score_is_python_weighted_sum(monkeypatch):
    rubric = get_rubric("ai_ml")
    dims = {d["key"]: 6.0 for d in rubric}

    def fake_call_tool(**_kwargs):
        return {**dims, "rationale": "ok", "strengths": "s", "gaps": "g"}

    monkeypatch.setattr(qg, "call_tool", fake_call_tool)
    result = qg.evaluate_answer("Q", "A", "ctx", "mid", role="ai_ml")
    assert result["score"] == weighted_score(dims, rubric)
    assert result["dimension_scores"] == dims


def test_evaluate_answer_raises_on_missing_rubric_dimension(monkeypatch):
    # A missing dimension must fail loudly, never silently score 0.
    def fake_call_tool(**_kwargs):
        return {"correctness": 8, "rationale": "r", "strengths": "s", "gaps": "g"}  # depth etc. missing

    monkeypatch.setattr(qg, "call_tool", fake_call_tool)
    with pytest.raises(ValueError, match="missing required rubric dimensions"):
        qg.evaluate_answer("Q", "A", "ctx", "mid", role="ai_ml")


def test_evaluate_answer_truncates_long_answer_in_prompt(monkeypatch):
    captured = {}
    rubric = get_rubric("ai_ml")

    def fake_call_tool(**kwargs):
        captured.update(kwargs)
        return {**{d["key"]: 5 for d in rubric}, "rationale": "", "strengths": "", "gaps": ""}

    monkeypatch.setattr(qg, "call_tool", fake_call_tool)
    qg.evaluate_answer("Q", "x" * 5000, "ctx", "mid", role="ai_ml")
    # answer capped at 1000 chars in the prompt
    assert "x" * 1001 not in captured["user_content"]


# --- evaluate_answer_with_consistency ---


def _stub_eval_by_stance(scores_by_stance):
    def stub(_q, _a, _c, _lvl, _role, stance):
        return {
            "score": scores_by_stance[stance],
            "dimension_scores": {},
            "rubric_version": "v1",
            "rationale": "r",
            "strengths": "s",
            "gaps": "g",
        }

    return stub


def test_consistency_flags_large_disagreement(monkeypatch):
    monkeypatch.setattr(qg, "evaluate_answer", _stub_eval_by_stance({"rigorous": 4.0, "lenient_check": 8.0}))
    result = qg.evaluate_answer_with_consistency("Q", "A", "ctx", "mid", role="ai_ml")
    assert result["score_variance"] == 4.0
    assert result["needs_human_review"] is True
    assert result["score"] == 4.0  # primary (rigorous) pass is the recorded one
    assert result["consistency_check_score"] == 8.0


def test_consistency_passes_close_scores(monkeypatch):
    monkeypatch.setattr(qg, "evaluate_answer", _stub_eval_by_stance({"rigorous": 7.0, "lenient_check": 7.5}))
    result = qg.evaluate_answer_with_consistency("Q", "A", "ctx", "mid", role="ai_ml")
    assert result["score_variance"] == 0.5
    assert result["needs_human_review"] is False


# --- generate_report ---


def test_generate_report_fallback_on_llm_failure(monkeypatch):
    def boom(**_kwargs):
        raise RuntimeError("provider down")

    monkeypatch.setattr(qg, "call_tool", boom)
    session_data = {"qa_pairs": [{"question": "Q1", "answer": "A1", "score": 6.0, "topic": "T"}], "candidate": {}}
    report = qg.generate_report(session_data)
    # Fallback is explicit about the failure and preserves the real average score.
    assert "failed" in report["summary"].lower()
    assert report["overall_score"] == 6.0
    assert report["recommendation"] == "maybe"


def test_generate_report_includes_transcript_and_avg(monkeypatch):
    captured = {}

    def fake_call_tool(**kwargs):
        captured.update(kwargs)
        return {
            "summary": "s",
            "overall_score": 7.0,
            "topic_coverage": {},
            "strengths": "",
            "gaps": "",
            "recommendation": "yes",
        }

    monkeypatch.setattr(qg, "call_tool", fake_call_tool)
    qg.generate_report(
        {
            "qa_pairs": [
                {"question": "What is SGD?", "answer": "Stochastic gradient descent", "score": 8.0, "topic": "Opt"},
                {"question": "Define recall", "answer": "TP / (TP+FN)", "score": 6.0, "topic": "Metrics"},
            ],
            "candidate": {"name": "Jane"},
            "role": "ai_ml",
        }
    )
    user = captured["user_content"]
    assert "What is SGD?" in user and "Define recall" in user
    assert "Average score: 7.0/10" in user


# --- _determine_focus ---


def test_focus_empty_for_first_two_questions():
    assert qg._determine_focus("short", [], 1) == ""
    assert qg._determine_focus("short", [], 2) == ""


def test_focus_falls_back_to_fundamentals_on_weak_answer():
    assert qg._determine_focus("too short", [], 3) == "fundamentals basics introduction"


def test_focus_empty_on_substantive_answer():
    assert qg._determine_focus("a" * 200, [], 3) == ""
