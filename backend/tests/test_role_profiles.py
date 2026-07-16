"""
Unit tests for role profile resolution (built-in + custom roles) and
LLM-generated profile creation, including its fallback path.
"""

import json

import pytest
from sqlalchemy.orm import sessionmaker

import app.services.role_profiles as rp
from app.models.session import CustomRole


@pytest.fixture()
def db(db_engine):
    session = sessionmaker(bind=db_engine)()
    yield session
    session.close()


def _add_custom_role(db, slug: str, persona=None, difficulty_guide=None):
    db.add(
        CustomRole(slug=slug, label=slug.replace("_", " ").title(), persona=persona, difficulty_guide=difficulty_guide)
    )
    db.commit()


# --- get_role_profile ---


def test_builtin_role_uses_builtin_persona_and_level(db):
    profile = rp.get_role_profile(db, "ai_ml", "senior")
    assert profile["persona"] == rp.BUILTIN_PERSONAS["ai_ml"]
    assert profile["difficulty"] == rp.BUILTIN_DIFFICULTY["senior"]


def test_unknown_experience_level_falls_back_to_mid(db):
    profile = rp.get_role_profile(db, "data_science", "wizard")
    assert profile["difficulty"] == rp.BUILTIN_DIFFICULTY["mid"]


def test_custom_role_with_stored_json_guide(db):
    guide = {"junior": "basics of embedded C", "mid": "RTOS trade-offs", "senior": "interrupt latency tuning"}
    _add_custom_role(
        db, "embedded_eng", persona="You are a principal embedded engineer.", difficulty_guide=json.dumps(guide)
    )
    profile = rp.get_role_profile(db, "embedded_eng", "senior")
    assert profile["persona"] == "You are a principal embedded engineer."
    assert profile["difficulty"] == "interrupt latency tuning"


def test_custom_role_json_guide_missing_level_falls_back_to_mid(db):
    _add_custom_role(
        db, "qa_eng", persona="You are a QA lead.", difficulty_guide=json.dumps({"mid": "test pyramid trade-offs"})
    )
    profile = rp.get_role_profile(db, "qa_eng", "senior")
    assert profile["difficulty"] == "test pyramid trade-offs"


def test_custom_role_with_plain_text_guide(db):
    _add_custom_role(db, "sre", persona="You are an SRE lead.", difficulty_guide="Focus on incident response.")
    profile = rp.get_role_profile(db, "sre", "mid")
    assert profile["difficulty"] == "Focus on incident response."


def test_missing_custom_role_gets_named_generic_persona(db):
    profile = rp.get_role_profile(db, "platform_eng", "mid")
    assert "platform eng" in profile["persona"]
    assert profile["difficulty"] == rp.BUILTIN_DIFFICULTY["mid"]


# --- generate_role_profile ---


def test_generate_role_profile_maps_tool_output(monkeypatch):
    def fake_call_tool(**_kwargs):
        return {
            "persona": "You are a staff frontend engineer conducting a technical screening interview.",
            "difficulty_junior": "DOM and CSS basics",
            "difficulty_mid": "state management trade-offs",
            "difficulty_senior": "rendering performance at scale",
        }

    monkeypatch.setattr(rp, "call_tool", fake_call_tool)
    profile = rp.generate_role_profile("Frontend Engineer", "Builds UIs", ["React"])
    assert profile["persona"].startswith("You are a staff frontend engineer")
    assert profile["difficulty_guide"] == {
        "junior": "DOM and CSS basics",
        "mid": "state management trade-offs",
        "senior": "rendering performance at scale",
    }


def test_generate_role_profile_fallback_never_hard_fails(monkeypatch):
    def boom(**_kwargs):
        raise RuntimeError("provider down")

    monkeypatch.setattr(rp, "call_tool", boom)
    profile = rp.generate_role_profile("Frontend Engineer", "", [])
    # Role creation must survive an LLM hiccup with a role-named generic profile.
    assert "Frontend Engineer" in profile["persona"]
    assert profile["difficulty_guide"] == rp.BUILTIN_DIFFICULTY
