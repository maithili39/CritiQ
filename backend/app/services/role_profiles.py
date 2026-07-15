"""
Role interviewing profiles: the persona + difficulty guidance that steer question
generation for a given role.

Before this, personas/difficulty guides were hardcoded per built-in slug in
question_generator, so a recruiter-created custom role silently fell back to a
generic "You are a senior engineer" persona — making the "role-based" part of
the product cosmetic for exactly the roles a recruiter cared enough to add.

Now every role resolves to a real profile:
- built-in roles use the constants below,
- custom roles use the persona/difficulty_guide stored on the CustomRole row,
  which are generated once at role-creation time (see generate_role_profile) from
  the role's label/description/topics if the recruiter doesn't supply them.

`get_role_profile` is the single lookup callers use; it never returns a generic
fallback for a custom role that has a stored profile.
"""

import logging

from sqlalchemy.orm import Session as DBSession

from app.core.config import settings
from app.services.llm import call_tool

logger = logging.getLogger(__name__)

BUILTIN_PERSONAS: dict[str, str] = {
    "ai_ml": "You are a senior AI/ML engineer conducting a technical screening interview.",
    "data_science": "You are a lead data scientist conducting a technical screening interview.",
}

# Per experience-level guidance. Keyed junior/mid/senior.
BUILTIN_DIFFICULTY: dict[str, str] = {
    "junior": "Focus on foundational concepts, definitions, and basic applications. Avoid deep math.",
    "mid": "Expect working knowledge. Ask about trade-offs, design choices, and real-world application.",
    "senior": "Probe deep understanding: edge cases, theoretical foundations, system design, and optimization.",
}

_GENERIC_PERSONA = "You are a senior engineer conducting a technical interview."

_ROLE_PROFILE_TOOL = {
    "name": "record_role_profile",
    "description": "Records the interviewer persona and difficulty guidance for a technical interview role.",
    "input_schema": {
        "type": "object",
        "properties": {
            "persona": {
                "type": "string",
                "description": (
                    "One sentence in the form 'You are a <senior role title> conducting a technical "
                    "screening interview.' — the interviewer voice for this role."
                ),
            },
            "difficulty_junior": {
                "type": "string",
                "description": "What to focus on when interviewing a junior candidate for this role.",
            },
            "difficulty_mid": {
                "type": "string",
                "description": "What to focus on when interviewing a mid-level candidate for this role.",
            },
            "difficulty_senior": {
                "type": "string",
                "description": "What to focus on when interviewing a senior candidate for this role.",
            },
        },
        "required": ["persona", "difficulty_junior", "difficulty_mid", "difficulty_senior"],
    },
}


def generate_role_profile(label: str, description: str, topics: list[str]) -> dict:
    """
    LLM-generates a persona + per-level difficulty guide for a custom role from its
    label/description/topics. Called once at role-creation time. Returns:
        {"persona": str, "difficulty_guide": {"junior": str, "mid": str, "senior": str}}

    Falls back to a generic-but-role-named profile if the model call fails, so role
    creation never hard-fails on an LLM hiccup.
    """
    topic_str = ", ".join(topics) if topics else "general topics for this role"
    user_content = (
        f"Role title: {label}\n"
        f"Description: {description or '(none provided)'}\n"
        f"Key topics: {topic_str}\n\n"
        "Produce the interviewer persona and difficulty guidance for screening candidates in this role."
    )
    try:
        result = call_tool(
            model=settings.LLM_MODEL,
            max_tokens=512,
            system=(
                "You define how a technical screening interview should be conducted for a given role. "
                "Be specific to the role — avoid generic phrasing that would fit any engineering job."
            ),
            user_content=user_content,
            tool=_ROLE_PROFILE_TOOL,
            cache_system=False,  # one-shot per role creation
        )
        return {
            "persona": result["persona"],
            "difficulty_guide": {
                "junior": result["difficulty_junior"],
                "mid": result["difficulty_mid"],
                "senior": result["difficulty_senior"],
            },
        }
    except Exception:
        logger.exception("Role profile generation failed for %r; using role-named fallback.", label)
        return {
            "persona": f"You are a senior {label} conducting a technical screening interview.",
            "difficulty_guide": dict(BUILTIN_DIFFICULTY),
        }


def get_role_profile(db: DBSession, role: str, experience_level: str) -> dict:
    """
    Resolves the persona + difficulty text to use for a role at a given level.
    Returns {"persona": str, "difficulty": str}.
    """
    if role in BUILTIN_PERSONAS:
        return {
            "persona": BUILTIN_PERSONAS[role],
            "difficulty": BUILTIN_DIFFICULTY.get(experience_level, BUILTIN_DIFFICULTY["mid"]),
        }

    # Custom role — read its stored profile.
    from app.models.session import CustomRole

    row = db.query(CustomRole).filter_by(slug=role).first()
    persona = (row.persona if row and row.persona else None) or f"You are a senior {role.replace('_', ' ')} conducting a technical screening interview."

    difficulty = BUILTIN_DIFFICULTY.get(experience_level, BUILTIN_DIFFICULTY["mid"])
    if row and row.difficulty_guide:
        import json

        try:
            guide = json.loads(row.difficulty_guide)
            if isinstance(guide, dict):
                difficulty = guide.get(experience_level) or guide.get("mid") or difficulty
            elif isinstance(guide, str):
                difficulty = guide
        except (ValueError, TypeError):
            difficulty = row.difficulty_guide  # stored as plain text

    return {"persona": persona, "difficulty": difficulty}
