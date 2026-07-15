"""
Single source of truth for valid interview roles.

Built-in roles (ai_ml, data_science) are defined here as constants.
Custom recruiter-defined roles live in the `custom_roles` DB table and are
merged at runtime via get_all_roles(db). All validation/enumeration should
call get_all_roles(db) rather than ALLOWED_ROLES directly when a DB session
is available; ALLOWED_ROLES is retained for import-time / CLI contexts that
don't have a DB session (e.g. config validation, alembic scripts).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Session as DBSession

# The ordered list is the canonical definition of built-in roles.
# Add new built-in roles here only — all validation/enumeration uses this module.
ROLES: list[str] = ["ai_ml", "data_science"]

# Frozenset for O(1) membership checks (e.g. `if role not in ALLOWED_ROLES`).
ALLOWED_ROLES: frozenset[str] = frozenset(ROLES)

ROLE_LABELS: dict[str, str] = {
    "ai_ml": "AI / ML Engineer",
    "data_science": "Data Scientist",
}

ROLE_DESCRIPTIONS: dict[str, str] = {
    "ai_ml": "Machine learning, deep learning, model development and deployment",
    "data_science": "Applied ML, statistical modeling, data analysis and visualization",
}

ROLE_TOPICS: dict[str, list[str]] = {
    "ai_ml": ["Neural Nets", "MLOps", "Transformers", "Model Eval"],
    "data_science": ["Statistics", "EDA", "Regression", "A/B Testing"],
}


def get_all_roles(db: DBSession) -> list[dict]:
    """
    Returns all roles (built-in + custom) as a list of dicts suitable for
    serialisation. Merges the static built-in definitions with any rows in
    the custom_roles table.

    Shape: [{slug, label, description, topics}, ...]
    """
    import json

    from app.models.session import CustomRole

    built_in = [
        {
            "slug": slug,
            "label": ROLE_LABELS.get(slug, slug),
            "description": ROLE_DESCRIPTIONS.get(slug, ""),
            "topics": ROLE_TOPICS.get(slug, []),
            "is_builtin": True,
        }
        for slug in ROLES
    ]

    custom = db.query(CustomRole).order_by(CustomRole.created_at).all()
    custom_list = [
        {
            "slug": r.slug,
            "label": r.label,
            "description": r.description or "",
            "topics": json.loads(r.topics or "[]"),
            "is_builtin": False,
        }
        for r in custom
    ]

    return built_in + custom_list


def get_all_role_slugs(db: DBSession) -> frozenset[str]:
    """Convenience wrapper: set of all valid role slugs (built-in + custom)."""
    return frozenset(r["slug"] for r in get_all_roles(db))
