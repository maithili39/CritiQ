"""Unit tests for session-level integrity fusion (deterministic, no LLM)."""

from app.services.integrity import compute_session_integrity


def test_clean_session_scores_high():
    answers = [
        {"score": 7, "response_time_ms": 60_000, "paste_detected": False, "tab_switch_count": 0},
        {"score": 6, "response_time_ms": 90_000, "paste_detected": False, "tab_switch_count": 0},
        {"score": 8, "response_time_ms": 75_000, "paste_detected": False, "tab_switch_count": 0},
    ]
    result = compute_session_integrity(answers)
    assert result["confidence"] == 100
    assert result["risk_level"] == "low"
    assert result["signals"] == []


def test_paste_and_tab_switches_penalized():
    answers = [
        {"score": 7, "response_time_ms": 60_000, "paste_detected": True, "tab_switch_count": 2},
        {"score": 6, "response_time_ms": 90_000, "paste_detected": False, "tab_switch_count": 0},
    ]
    result = compute_session_integrity(answers)
    assert result["confidence"] < 100
    codes = {s["code"] for s in result["signals"]}
    assert "paste_events" in codes
    assert "tab_switches" in codes


def test_fast_high_score_spike_is_strongest_signal():
    # Three normal answers plus one that is dramatically faster AND scored high.
    answers = [
        {"score": 6, "response_time_ms": 80_000, "paste_detected": False, "tab_switch_count": 0},
        {"score": 6, "response_time_ms": 85_000, "paste_detected": False, "tab_switch_count": 0},
        {"score": 6, "response_time_ms": 90_000, "paste_detected": False, "tab_switch_count": 0},
        {"score": 9, "response_time_ms": 4_000, "paste_detected": False, "tab_switch_count": 0},
    ]
    result = compute_session_integrity(answers)
    codes = {s["code"] for s in result["signals"]}
    assert "fast_high_score_spike" in codes
    # One spike dents confidence but isn't damning on its own.
    assert result["confidence"] < 100


def test_uniform_fast_alone_is_weaker_than_a_spike():
    # A uniformly-fast strong candidate should not be flagged as harshly as a spike.
    uniform = compute_session_integrity(
        [{"score": 8, "response_time_ms": 10_000, "paste_detected": False, "tab_switch_count": 0} for _ in range(4)]
    )
    spike = compute_session_integrity(
        [
            {"score": 6, "response_time_ms": 80_000, "paste_detected": False, "tab_switch_count": 0},
            {"score": 6, "response_time_ms": 85_000, "paste_detected": False, "tab_switch_count": 0},
            {"score": 6, "response_time_ms": 90_000, "paste_detected": False, "tab_switch_count": 0},
            {"score": 9, "response_time_ms": 3_000, "paste_detected": False, "tab_switch_count": 0},
        ]
    )
    assert uniform["confidence"] > spike["confidence"]


def test_missing_telemetry_degrades_gracefully():
    result = compute_session_integrity([{"score": 7}, {"score": 8}])
    assert result["confidence"] == 100
    assert result["answers_analyzed"] == 2
