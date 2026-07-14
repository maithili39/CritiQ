"""
Single source of truth for valid interview roles.

Previously ROLES was defined independently in both app/api/admin.py and
app/api/sessions.py as two different objects (list vs set), creating a risk
of silent drift whenever a role was added or removed in one file but not
the other. Everything that needs to check or enumerate roles imports from
here instead.
"""

# The ordered list is the canonical definition.
# add new roles here only — all validation/enumeration uses this module.
ROLES: list[str] = ["ai_ml", "data_science"]

# Frozenset for O(1) membership checks (e.g. `if role not in ALLOWED_ROLES`).
ALLOWED_ROLES: frozenset[str] = frozenset(ROLES)

ROLE_LABELS: dict[str, str] = {
    "ai_ml": "AI / ML Engineer",
    "data_science": "Data Scientist",
}
