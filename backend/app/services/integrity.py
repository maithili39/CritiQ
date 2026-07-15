"""
Session-level integrity fusion.

The per-answer integrity_flags are independent boolean rules (paste? tab-switch?
sub-15s?). Each in isolation is both easy to game and easy to trip innocently —
a fast typist on an easy question looks identical to a cheater on one answer.

This module fuses those signals across the WHOLE session into one 0-100
confidence score plus a risk level, and adds signals that only exist at the
session level:

- Response-time consistency: a genuine candidate's answer times vary with
  question difficulty. An answer that is a dramatic outlier against that
  candidate's own distribution (a single very fast, high-scoring spike among
  otherwise normal times) is more suspicious than uniformly fast answers, which
  more often just mean an easy question set or a strong candidate.
- Fast-AND-correct coupling: fast alone is weak; fast + high score + paste/tab
  signals compound.

The output is deterministic and explainable (every point of deduction is listed
in `signals`), so a recruiter sees *why* a session is flagged, not just a number.
"""

from statistics import mean, pstdev


def compute_session_integrity(answers: list[dict]) -> dict:
    """
    `answers`: list of dicts with keys score, response_time_ms, paste_detected,
    tab_switch_count (all optional/nullable — telemetry degrades gracefully).

    Returns:
        {
          "confidence": int 0-100,   # 100 = fully clean, low = suspicious
          "risk_level": "low"|"medium"|"high",
          "signals": [ {code, detail, weight}, ... ],
          "answers_analyzed": int,
        }
    """
    timed = [a for a in answers if a.get("response_time_ms") is not None]
    signals: list[dict] = []
    penalty = 0

    # --- Aggregate hard signals across the session ---
    paste_count = sum(1 for a in answers if a.get("paste_detected"))
    tab_total = sum((a.get("tab_switch_count") or 0) for a in answers)

    if paste_count:
        w = min(25, 12 + 6 * paste_count)
        penalty += w
        signals.append({"code": "paste_events", "detail": f"{paste_count} answer(s) with paste", "weight": w})
    if tab_total:
        w = min(20, 5 + 3 * tab_total)
        penalty += w
        signals.append({"code": "tab_switches", "detail": f"{tab_total} tab switch(es) total", "weight": w})

    # --- Response-time distribution analysis (needs >= 3 timed answers) ---
    if len(timed) >= 3:
        times = [a["response_time_ms"] for a in timed]
        mu = mean(times)
        sigma = pstdev(times)

        # Outlier spikes: an answer far below the candidate's own mean, i.e. an
        # anomalously fast answer relative to how they answered everything else.
        if sigma > 0:
            fast_spikes = [
                a for a in timed
                if (mu - a["response_time_ms"]) / sigma > 1.5 and a["response_time_ms"] < 20_000
            ]
            # A fast spike that ALSO scored high is the strongest single signal:
            # cheaters paste a perfect answer far faster than they wrote the others.
            fast_high = [a for a in fast_spikes if (a.get("score") or 0) >= 8]
            if fast_high:
                w = min(30, 15 * len(fast_high))
                penalty += w
                signals.append(
                    {
                        "code": "fast_high_score_spike",
                        "detail": f"{len(fast_high)} answer(s) far faster than the candidate's norm yet scored 8+",
                        "weight": w,
                    }
                )
            elif fast_spikes:
                w = min(15, 7 * len(fast_spikes))
                penalty += w
                signals.append(
                    {
                        "code": "response_time_spike",
                        "detail": f"{len(fast_spikes)} answer(s) anomalously fast vs. this candidate's own pace",
                        "weight": w,
                    }
                )

        # Uniform near-instant answers across the board (all under 15s) — weaker,
        # since it can be an easy set, but worth surfacing when combined with score.
        if all(t < 15_000 for t in times) and mean(a.get("score") or 0 for a in timed) >= 7:
            penalty += 12
            signals.append(
                {
                    "code": "uniformly_instant",
                    "detail": "every answer under 15s with consistently high scores",
                    "weight": 12,
                }
            )

    confidence = max(0, 100 - penalty)
    risk_level = "low" if confidence >= 75 else "medium" if confidence >= 50 else "high"

    return {
        "confidence": confidence,
        "risk_level": risk_level,
        "signals": signals,
        "answers_analyzed": len(answers),
    }
