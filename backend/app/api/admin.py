"""Admin endpoints for knowledge base management and role registry."""

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession

from app.api.deps import require_admin_api_key
from app.core.database import get_db
from app.core.roles import ROLES, get_all_roles
from app.models.session import CustomRole
from app.rag.ingestion import get_collection, ingest_role_documents
from app.schemas.interview import CustomRoleCreate
from app.services.role_profiles import generate_role_profile

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin_api_key)])


# ---------------------------------------------------------------------------
# Knowledge-base ingestion
# ---------------------------------------------------------------------------

@router.post("/ingest/{role}")
def ingest_knowledge_base(role: str, force: bool = False, db: DBSession = Depends(get_db)):
    """Trigger ingestion of PDFs for a given role into ChromaDB.

    Accepts any role slug — both built-in roles and custom roles created via
    POST /admin/roles — as long as a knowledge_base/<slug>/ directory exists.
    Pass 'all' to re-ingest all built-in roles.
    """
    all_slugs = {r["slug"] for r in get_all_roles(db)}

    if role != "all" and role not in all_slugs:
        raise HTTPException(400, f"Role must be one of: {', '.join(sorted(all_slugs))} or 'all'")

    roles_to_ingest = ROLES if role == "all" else [role]

    results = {}
    for r in roles_to_ingest:
        try:
            count = ingest_role_documents(r, force_reingest=force)
            results[r] = {"status": "ok", "chunks": count}
        except Exception as e:
            results[r] = {"status": "error", "error": str(e)}

    return {"results": results}


@router.get("/knowledge-base/status")
def knowledge_base_status(db: DBSession = Depends(get_db)):
    """Check how many chunks are stored per role (built-in + custom)."""
    all_roles = get_all_roles(db)
    status = {}
    for role in all_roles:
        slug = role["slug"]
        try:
            collection = get_collection(slug)
            status[slug] = {
                "label": role["label"],
                "chunks": collection.count(),
                "status": "ready" if collection.count() > 0 else "empty",
            }
        except Exception as e:
            status[slug] = {"label": role["label"], "chunks": 0, "status": "error", "error": str(e)}
    return status


# ---------------------------------------------------------------------------
# Custom role registry
# ---------------------------------------------------------------------------

@router.post("/roles", response_model=dict, status_code=201)
def create_custom_role(payload: CustomRoleCreate, db: DBSession = Depends(get_db)):
    """Create a new custom interview role track.

    The slug must be unique across both built-in and custom roles. After
    creating a role, upload knowledge-base PDFs to knowledge_base/<slug>/
    and call POST /admin/ingest/<slug> to populate ChromaDB.
    """
    # Guard against slug collisions with built-in roles
    all_slugs = {r["slug"] for r in get_all_roles(db)}
    if payload.slug in all_slugs:
        raise HTTPException(409, f"Role slug '{payload.slug}' already exists.")

    # Resolve the interviewing profile: use recruiter-supplied persona/difficulty if
    # given, otherwise LLM-generate them from the role's label/description/topics so
    # the custom role drives question generation instead of falling back to generic.
    if payload.persona and payload.difficulty_guide:
        persona = payload.persona
        difficulty_guide = payload.difficulty_guide
    else:
        generated = generate_role_profile(payload.label, payload.description or "", payload.topics)
        persona = payload.persona or generated["persona"]
        difficulty_guide = payload.difficulty_guide or json.dumps(generated["difficulty_guide"])

    role = CustomRole(
        slug=payload.slug,
        label=payload.label,
        description=payload.description,
        topics=json.dumps(payload.topics),
        persona=persona,
        difficulty_guide=difficulty_guide,
    )
    db.add(role)
    db.commit()
    db.refresh(role)

    return {
        "slug": role.slug,
        "label": role.label,
        "description": role.description,
        "topics": payload.topics,
        "persona": role.persona,
        "created_at": role.created_at.isoformat(),
        "message": f"Role '{role.label}' created. Add PDFs to knowledge_base/{role.slug}/ and call /admin/ingest/{role.slug}.",
    }


@router.get("/roles", response_model=dict)
def list_all_roles(db: DBSession = Depends(get_db)):
    """List all available interview roles (built-in + custom)."""
    return {"roles": get_all_roles(db)}


@router.delete("/roles/{slug}", response_model=dict)
def delete_custom_role(slug: str, db: DBSession = Depends(get_db)):
    """Delete a custom role. Built-in roles cannot be deleted."""
    if slug in ROLES:
        raise HTTPException(400, f"'{slug}' is a built-in role and cannot be deleted.")

    role = db.query(CustomRole).filter_by(slug=slug).first()
    if not role:
        raise HTTPException(404, f"Custom role '{slug}' not found.")

    db.delete(role)
    db.commit()
    return {"message": f"Role '{slug}' deleted."}
