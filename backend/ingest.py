"""
CLI script to ingest knowledge base PDFs into ChromaDB.

Usage:
    python ingest.py --role ai_ml
    python ingest.py --role data_science
    python ingest.py --role all
    python ingest.py --role all --force   # re-ingest from scratch
"""

import argparse
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s — %(message)s")

from app.rag.ingestion import ingest_role_documents

ROLES = ["ai_ml", "data_science"]


def main():
    parser = argparse.ArgumentParser(description="Ingest knowledge base PDFs into ChromaDB.")
    parser.add_argument("--role", required=True, choices=[*ROLES, "all"])
    parser.add_argument("--force", action="store_true", help="Force re-ingestion even if already done")
    args = parser.parse_args()

    roles = ROLES if args.role == "all" else [args.role]

    for role in roles:
        print(f"\n=== Ingesting role: {role} ===")
        count = ingest_role_documents(role, force_reingest=args.force)
        print(f"✓ {role}: {count} chunks stored")

    print("\nIngestion complete.")


if __name__ == "__main__":
    main()
