"""Admin endpoints for knowledge base management."""

from fastapi import APIRouter, Depends, HTTPException
from app.api.deps import require_admin_api_key
from app.rag.ingestion import ingest_role_documents, get_collection

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin_api_key)])

ROLES = ["ai_ml", "data_science"]


@router.post("/ingest/{role}")
def ingest_knowledge_base(role: str, force: bool = False):
    """Trigger ingestion of PDFs for a given role into ChromaDB."""
    if role not in ROLES and role != "all":
        raise HTTPException(400, f"Role must be one of: {', '.join(ROLES)} or 'all'")

    results = {}
    roles_to_ingest = ROLES if role == "all" else [role]

    for r in roles_to_ingest:
        try:
            count = ingest_role_documents(r, force_reingest=force)
            results[r] = {"status": "ok", "chunks": count}
        except Exception as e:
            results[r] = {"status": "error", "error": str(e)}

    return {"results": results}


@router.get("/knowledge-base/status")
def knowledge_base_status():
    """Check how many chunks are stored per role."""
    status = {}
    for role in ROLES:
        try:
            collection = get_collection(role)
            status[role] = {"chunks": collection.count(), "status": "ready" if collection.count() > 0 else "empty"}
        except Exception as e:
            status[role] = {"chunks": 0, "status": "error", "error": str(e)}
    return status
