"""
Resume Parser Service

Extracts structured info from raw resume text using Claude.
Output drives RAG query construction and question difficulty calibration.
"""

import logging
from typing import Dict

import fitz  # PyMuPDF

from app.core.config import settings
from app.services.llm import call_tool

logger = logging.getLogger(__name__)

_SYSTEM = """You are a technical recruiter assistant. Analyze the candidate's resume text
and extract structured information via the extract_resume_profile tool. Base every field
strictly on what's stated or clearly implied in the resume — do not invent skills or
experience that aren't there."""

_TOOL = {
    "name": "extract_resume_profile",
    "description": "Records structured profile data extracted from a candidate's resume.",
    "input_schema": {
        "type": "object",
        "properties": {
            "skills": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Technical skills, concepts, and methodologies.",
            },
            "technologies": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Tools, frameworks, languages, and platforms.",
            },
            "experience_level": {
                "type": "string",
                "enum": ["junior", "mid", "senior"],
                "description": "Based on years and depth of experience.",
            },
            "domains": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Knowledge domains, e.g. machine learning, computer vision, NLP, backend.",
            },
            "years_of_experience": {
                "type": ["integer", "null"],
                "description": "Total years of relevant professional experience, or null if unclear.",
            },
            "education": {
                "type": "string",
                "description": "Highest relevant degree and field.",
            },
            "summary": {
                "type": "string",
                "description": "2-3 sentence professional summary of this candidate.",
            },
        },
        "required": ["skills", "technologies", "experience_level", "domains", "education", "summary"],
    },
}


def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text("text") + "\n"
    doc.close()
    return text.strip()


def parse_resume(resume_text: str) -> Dict:
    """
    Uses Claude to extract structured data from resume text.

    Returns:
        {
            skills: list[str],
            technologies: list[str],
            experience_level: "junior" | "mid" | "senior",
            domains: list[str],
            years_of_experience: int | None,
            education: str,
            summary: str
        }
    """
    try:
        return call_tool(
            model=settings.CLAUDE_MODEL,
            max_tokens=1024,
            system=_SYSTEM,
            user_content=f"RESUME TEXT:\n{resume_text[:6000]}",
            tool=_TOOL,
            cache_system=False,  # parse_resume runs once per session; nothing to reuse across calls
        )
    except Exception:
        logger.exception("Resume parsing failed; falling back to an empty profile.")
        return {
            "skills": [],
            "technologies": [],
            "experience_level": "mid",
            "domains": [],
            "years_of_experience": None,
            "education": "",
            "summary": resume_text[:300],
        }
