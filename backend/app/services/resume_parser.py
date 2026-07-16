"""
Resume Parser Service

Extracts structured info from raw resume text using Claude.
Output drives RAG query construction and question difficulty calibration.
"""

import logging
import re

import fitz  # PyMuPDF

from app.core.config import settings
from app.services.llm import call_tool

logger = logging.getLogger(__name__)

_SYSTEM = """You are a technical recruiter assistant. Analyze the candidate's resume text
and extract structured information via the extract_resume_profile tool. Base every field
strictly on what's stated or clearly implied in the resume — do not invent skills or
experience that aren't there.

The resume may have had personally identifying and demographic details redacted (shown as
[REDACTED]). Never attempt to infer, guess, or reconstruct a candidate's name, gender, age,
ethnicity, nationality, or any other protected attribute, and never let such attributes
influence the extracted profile. Evaluate skills and experience only."""

# --- Demographic-blind redaction (fairness / bias mitigation) ---
#
# Strips contact details, links, and explicit demographic markers from resume text
# BEFORE it reaches the LLM, so the extracted profile cannot be swayed by who the
# candidate is — only by what they can do. Regex-based and deterministic: it never
# calls the model and cannot itself leak data.
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
_URL_RE = re.compile(r"\b(?:https?://|www\.)\S+", re.IGNORECASE)
# Phone numbers: 7+ digits allowing spaces, dashes, dots, parens, and a leading +.
_PHONE_RE = re.compile(r"(?<!\w)\+?\(?\d[\d\s().\-]{6,}\d(?!\w)")
# Explicit demographic lines, e.g. "Gender: Female", "Date of Birth: 1997", "Age: 27".
_DEMOGRAPHIC_RE = re.compile(
    r"(?im)^\s*(gender|sex|age|date\s*of\s*birth|d\.?o\.?b\.?|nationality|marital\s*status|"
    r"religion|race|ethnicity)\s*[:\-].*$"
)


def redact_pii(text: str) -> str:
    """Redact contact info, links, and explicit demographic markers from resume text.

    Order matters: emails and URLs are removed before phone matching so an email's or
    URL's digits aren't mistaken for a phone number.
    """
    text = _EMAIL_RE.sub("[REDACTED]", text)
    text = _URL_RE.sub("[REDACTED]", text)
    text = _PHONE_RE.sub("[REDACTED]", text)
    text = _DEMOGRAPHIC_RE.sub("[REDACTED]", text)
    return text

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
    # Some PDFs yield embedded NUL bytes, which Postgres text columns reject outright.
    return text.replace("\x00", "").strip()


def parse_resume(resume_text: str) -> dict:
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
    if settings.BLIND_SCREENING:
        resume_text = redact_pii(resume_text)
    try:
        return call_tool(
            model=settings.LLM_MODEL,
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
