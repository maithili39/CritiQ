"""
Question Generation Service

Uses retrieved RAG context + candidate resume profile to generate
targeted, non-generic interview questions via Claude.

Design:
- Questions are generated one at a time (not batch) so each can adapt
  to the previous answer when adaptive mode is on.
- Source context is stored with each question for full traceability.
- Difficulty is calibrated from experience_level in the parsed resume.
- All three Claude calls (question, evaluation, report) use tool-use with a
  forced tool_choice, so the response is guaranteed to match the schema —
  no markdown-fence stripping or JSON-parse retry loop needed.
"""

import logging
from typing import Dict, List, Optional

from app.core.config import settings
from app.rag.retriever import retrieve_for_question_generation
from app.services.llm import call_tool

logger = logging.getLogger(__name__)

DIFFICULTY_GUIDE = {
    "junior": "Focus on foundational concepts, definitions, and basic applications. Avoid deep math.",
    "mid": "Expect working knowledge. Ask about trade-offs, design choices, and real-world application.",
    "senior": "Probe deep understanding: edge cases, theoretical foundations, system design, and optimization.",
}

ROLE_PERSONAS = {
    "ai_ml": "You are a senior AI/ML engineer conducting a technical screening interview.",
    "data_science": "You are a lead data scientist conducting a technical screening interview.",
}

QUESTION_TYPES = [
    "conceptual",       # explain a concept
    "applied",          # how would you use X in practice
    "scenario",         # given this situation, what would you do
    "debugging",        # why might X fail / what could go wrong
    "design",           # how would you design/build X
]

_GENERATE_QUESTION_TOOL = {
    "name": "generate_interview_question",
    "description": "Records the next technical interview question to ask the candidate.",
    "input_schema": {
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "The interview question to ask."},
            "topic": {"type": "string", "description": "Main topic being tested, e.g. 'Gradient Descent', 'Overfitting'."},
            "rationale": {"type": "string", "description": "1 sentence: why this question for this candidate."},
        },
        "required": ["text", "topic", "rationale"],
    },
}

_EVALUATE_ANSWER_TOOL = {
    "name": "evaluate_interview_answer",
    "description": "Records the evaluation of a candidate's interview answer.",
    "input_schema": {
        "type": "object",
        "properties": {
            "score": {"type": "number", "minimum": 0, "maximum": 10, "description": "Score from 0-10."},
            "rationale": {"type": "string", "description": "2-3 sentence overall assessment."},
            "strengths": {"type": "string", "description": "What the candidate got right."},
            "gaps": {"type": "string", "description": "What was missing or incorrect."},
        },
        "required": ["score", "rationale", "strengths", "gaps"],
    },
}

_GENERATE_REPORT_TOOL = {
    "name": "generate_hiring_report",
    "description": "Records the final hiring assessment report for a completed interview.",
    "input_schema": {
        "type": "object",
        "properties": {
            "summary": {"type": "string", "description": "3-4 sentence overall assessment of the candidate."},
            "overall_score": {"type": "number", "minimum": 0, "maximum": 10},
            "topic_coverage": {
                "type": "object",
                "additionalProperties": {"type": "number"},
                "description": "Map of topic name to score 0-10.",
            },
            "strengths": {"type": "string", "description": "Key technical strengths demonstrated."},
            "gaps": {"type": "string", "description": "Knowledge gaps or areas of improvement."},
            "recommendation": {"type": "string", "enum": ["strong_yes", "yes", "maybe", "no"]},
        },
        "required": ["summary", "overall_score", "topic_coverage", "strengths", "gaps", "recommendation"],
    },
}


def generate_question(
    role: str,
    parsed_resume: Dict,
    previous_questions: List[str],
    previous_answer: Optional[str] = None,
    question_number: int = 1,
) -> Dict:
    """
    Generates the next interview question grounded in RAG context.

    Returns:
        {
            text: str,
            topic: str,
            difficulty: str,
            source_context: str,
            question_type: str,
            sources: list
        }
    """
    previous_topics = _extract_topics_from_questions(previous_questions)
    focus = _determine_focus(previous_answer, previous_topics, question_number)

    retrieval = retrieve_for_question_generation(
        role=role,
        parsed_resume=parsed_resume,
        previous_topics=previous_topics,
        focus_topic=focus,
    )

    experience_level = retrieval["experience_level"]
    difficulty_guide = DIFFICULTY_GUIDE.get(experience_level, DIFFICULTY_GUIDE["mid"])
    persona = ROLE_PERSONAS.get(role, "You are a senior engineer conducting a technical interview.")
    question_type = QUESTION_TYPES[(question_number - 1) % len(QUESTION_TYPES)]

    # Static across every generate_question call for this role/level — cached so an
    # 8-question session only pays full input-token cost on the first call.
    system = f"""{persona}

DIFFICULTY GUIDANCE: {difficulty_guide}

TASK: Generate one interview question of type "{question_type}" using the
generate_interview_question tool. The question must:
1. Be directly grounded in the knowledge base context provided in the user message
2. Be specific to the candidate's background (not generic)
3. Test {question_type} understanding
4. Match the difficulty level for a {experience_level} candidate"""

    prev_q_text = ""
    if previous_questions:
        prev_q_text = "Previously asked questions (DO NOT repeat these topics):\n" + "\n".join(
            f"- {q}" for q in previous_questions[-3:]
        )

    adaptive_text = ""
    if previous_answer and question_number > 1:
        adaptive_text = f"""
The candidate's last answer was:
\"\"\"{previous_answer[:600]}\"\"\"

Consider their demonstrated understanding when choosing depth and angle for the next question.
If they showed strong knowledge, go deeper. If they struggled, probe fundamentals."""

    user_content = f"""CANDIDATE PROFILE:
- Experience level: {experience_level}
- Skills: {", ".join(retrieval["query_skills"][:10])}
- Summary: {parsed_resume.get("summary", "")}

KNOWLEDGE BASE CONTEXT (use this as the grounding source):
{retrieval["context_text"][:3000]}

{prev_q_text}
{adaptive_text}

Generate question #{question_number}."""

    try:
        result = call_tool(
            model=settings.CLAUDE_MODEL,
            max_tokens=512,
            system=system,
            user_content=user_content,
            tool=_GENERATE_QUESTION_TOOL,
        )
    except Exception:
        logger.exception("Question generation failed; using fallback question.")
        result = {
            "text": "Describe a key concept relevant to this role and how you've applied it.",
            "topic": "General",
            "rationale": "Fallback question — the model call failed.",
        }

    result["difficulty"] = experience_level
    result["question_type"] = question_type
    result["source_context"] = retrieval["context_text"][:1500]
    result["sources"] = retrieval["sources"]
    return result


def evaluate_answer(question: str, answer: str, context: str, experience_level: str) -> Dict:
    """
    Evaluates a candidate's answer using Claude.
    Returns {score: float (0-10), rationale: str, strengths: str, gaps: str}
    """
    # Static across every evaluate_answer call in a session — cached.
    system = "You are evaluating a technical interview answer. Be fair but rigorous."

    user_content = f"""Question: {question}

Expected knowledge context:
{context[:1500]}

Candidate's answer:
\"\"\"{answer[:1000]}\"\"\"

Candidate level: {experience_level}"""

    # No fake neutral fallback score on failure — a candidate's grade should never
    # come from a masked error. call_tool/create_message raise on failure, which
    # the caller (interview_orchestrator -> API layer) surfaces as a 500 to retry.
    return call_tool(
        model=settings.CLAUDE_MODEL,
        max_tokens=512,
        system=system,
        user_content=user_content,
        tool=_EVALUATE_ANSWER_TOOL,
    )


def generate_report(session_data: Dict) -> Dict:
    """
    Generates the final session report with insights and recommendation.
    """
    qa_pairs = session_data.get("qa_pairs", [])
    candidate = session_data.get("candidate", {})
    role = session_data.get("role", "")

    qa_text = ""
    for i, pair in enumerate(qa_pairs, 1):
        qa_text += f"\nQ{i} [{pair.get('topic', '')}]: {pair.get('question', '')}\n"
        qa_text += f"A{i}: {pair.get('answer', '')[:400]}\n"
        if pair.get("score") is not None:
            qa_text += f"Score: {pair['score']}/10\n"

    scores = [p["score"] for p in qa_pairs if p.get("score") is not None]
    avg_score = round(sum(scores) / len(scores), 1) if scores else 0

    system = "You are generating a hiring assessment report. Base the recommendation on: " \
             "strong_yes (8+), yes (6.5-8), maybe (5-6.5), no (<5)."

    user_content = f"""Candidate: {candidate.get("name", "Candidate")}
Role: {role.replace("_", " ").title()}
Experience level: {candidate.get("experience_level", "mid")}
Average score: {avg_score}/10

Interview transcript:
{qa_text[:4000]}"""

    try:
        return call_tool(
            model=settings.CLAUDE_MODEL,
            max_tokens=800,
            system=system,
            user_content=user_content,
            tool=_GENERATE_REPORT_TOOL,
            cache_system=False,  # generate_report runs once per session; nothing to reuse
        )
    except Exception:
        logger.exception("Report generation failed; using fallback summary.")
        return {
            "summary": "Report generation failed — the model call did not succeed. Please retry.",
            "overall_score": avg_score,
            "topic_coverage": {},
            "strengths": "",
            "gaps": "",
            "recommendation": "maybe",
        }


def _extract_topics_from_questions(questions: List[str]) -> List[str]:
    """Naive topic extraction from question text for de-duplication."""
    return questions  # The retriever uses these as negative signals via the prompt


def _determine_focus(previous_answer: Optional[str], previous_topics: List[str], question_number: int) -> str:
    """Determines focus area for retrieval based on session progress."""
    if question_number <= 2:
        return ""
    if previous_answer and len(previous_answer) < 80:
        return "fundamentals basics introduction"
    return ""
