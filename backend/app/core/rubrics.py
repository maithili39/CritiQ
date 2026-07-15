"""
Per-role scoring rubrics.

Answer scoring used to be "ask Claude for a single 0-10 number" — no auditable
basis for the grade, and no way to tell a confident-but-wrong LLM judgment from
a genuinely rigorous one. Rubrics fix the first problem: each role defines
weighted dimensions, Claude scores each dimension independently (still a
judgment call, but a narrower, more consistent one per-dimension), and the
final score is a weighted sum computed in Python — not asked of the model —
so the aggregation is deterministic and reviewable after the fact.

RUBRIC_VERSION is stored on every Answer so that if a rubric's weights/
dimensions change later, old scores remain interpretable against the rubric
that actually produced them instead of silently drifting.
"""

RUBRIC_VERSION = "v1"

Dimension = dict  # {"key": str, "label": str, "weight": float, "description": str}

RUBRICS: dict[str, list[Dimension]] = {
    "ai_ml": [
        {
            "key": "correctness",
            "label": "Technical Correctness",
            "weight": 0.4,
            "description": "Is the core technical claim accurate — no factual errors about the underlying ML/DL concept?",
        },
        {
            "key": "depth",
            "label": "Depth of Understanding",
            "weight": 0.3,
            "description": "Does the answer go beyond a definition into trade-offs, failure modes, or reasoning about why, not just what?",
        },
        {
            "key": "applied_reasoning",
            "label": "Applied Reasoning",
            "weight": 0.2,
            "description": "Can the candidate connect the concept to a practical scenario, implementation detail, or real system?",
        },
        {
            "key": "communication",
            "label": "Communication Clarity",
            "weight": 0.1,
            "description": "Is the explanation structured and clear enough that a colleague could follow it?",
        },
    ],
    "data_science": [
        {
            "key": "correctness",
            "label": "Statistical/Technical Correctness",
            "weight": 0.4,
            "description": "Is the statistical or methodological claim accurate?",
        },
        {
            "key": "depth",
            "label": "Depth of Understanding",
            "weight": 0.3,
            "description": "Does the answer address assumptions, caveats, or edge cases rather than a surface-level definition?",
        },
        {
            "key": "applied_reasoning",
            "label": "Applied Reasoning",
            "weight": 0.2,
            "description": "Can the candidate ground the concept in a real dataset/analysis/business decision?",
        },
        {
            "key": "communication",
            "label": "Communication Clarity",
            "weight": 0.1,
            "description": "Is the explanation structured and clear enough that a colleague could follow it?",
        },
    ],
}

# Used for custom (recruiter-defined) roles that don't have a hand-tuned rubric yet.
DEFAULT_RUBRIC: list[Dimension] = [
    {
        "key": "correctness",
        "label": "Technical Correctness",
        "weight": 0.45,
        "description": "Is the core technical claim accurate for this field?",
    },
    {
        "key": "depth",
        "label": "Depth of Understanding",
        "weight": 0.35,
        "description": "Does the answer show reasoning beyond a memorized definition?",
    },
    {
        "key": "communication",
        "label": "Communication Clarity",
        "weight": 0.20,
        "description": "Is the explanation clear and well-structured?",
    },
]


def get_rubric(role: str) -> list[Dimension]:
    return RUBRICS.get(role, DEFAULT_RUBRIC)


def weighted_score(dimension_scores: dict[str, float], rubric: list[Dimension]) -> float:
    """Deterministic weighted aggregation — the number Claude never computes itself."""
    total_weight = sum(d["weight"] for d in rubric)
    total = sum(dimension_scores.get(d["key"], 0) * d["weight"] for d in rubric)
    return round(total / total_weight, 2) if total_weight else 0.0
