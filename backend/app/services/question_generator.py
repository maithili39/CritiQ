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
from concurrent.futures import ThreadPoolExecutor

from app.core.config import settings
from app.core.rubrics import RUBRIC_VERSION, get_rubric, weighted_score
from app.rag.retriever import retrieve_for_question_generation
from app.services.llm import call_tool

logger = logging.getLogger(__name__)

# Score disagreement above this threshold (0-10 scale) between the two independent
# evaluation passes gets flagged for human review rather than trusted blindly.
CONSISTENCY_VARIANCE_THRESHOLD = 1.5

QUESTION_TYPES = [
    "conceptual",  # explain a concept
    "applied",  # how would you use X in practice
    "scenario",  # given this situation, what would you do
    "debugging",  # why might X fail / what could go wrong
    "design",  # how would you design/build X
]

_GENERATE_QUESTION_TOOL = {
    "name": "generate_interview_question",
    "description": "Records the next technical interview question to ask the candidate.",
    "input_schema": {
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "The interview question to ask."},
            "topic": {
                "type": "string",
                "description": "Main topic being tested, e.g. 'Gradient Descent', 'Overfitting'.",
            },
            "rationale": {"type": "string", "description": "1 sentence: why this question for this candidate."},
        },
        "required": ["text", "topic", "rationale"],
    },
}


def _build_evaluate_answer_tool(rubric: list[dict]) -> dict:
    """
    Builds the tool schema for a rubric: one required 0-10 field per dimension,
    forcing Claude to score each dimension independently instead of a single
    holistic number. The weighted total is computed afterwards in Python
    (see rubrics.weighted_score), not asked of the model.
    """
    dimension_props = {
        d["key"]: {
            "type": "number",
            "minimum": 0,
            "maximum": 10,
            "description": f"{d['label']}: {d['description']}",
        }
        for d in rubric
    }
    return {
        "name": "evaluate_interview_answer",
        "description": "Records a per-dimension rubric evaluation of a candidate's interview answer.",
        "input_schema": {
            "type": "object",
            "properties": {
                **dimension_props,
                "rationale": {"type": "string", "description": "2-3 sentence overall assessment."},
                "strengths": {"type": "string", "description": "What the candidate got right."},
                "gaps": {"type": "string", "description": "What was missing or incorrect."},
            },
            "required": [*dimension_props.keys(), "rationale", "strengths", "gaps"],
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
    parsed_resume: dict,
    previous_questions: list[str],
    previous_answer: str | None = None,
    question_number: int = 1,
    role_profile: dict | None = None,
) -> dict:
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
    # role_profile resolves persona + difficulty for both built-in and custom roles
    # (see role_profiles.get_role_profile). Passed in by the orchestrator, which has
    # the DB session; falls back to a generic persona only if none was provided.
    if role_profile:
        persona = role_profile["persona"]
        difficulty_guide = role_profile["difficulty"]
    else:
        persona = "You are a senior engineer conducting a technical interview."
        difficulty_guide = "Expect working knowledge. Ask about trade-offs and real-world application."
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

    # No silent fallback — a fake placeholder question reaching the candidate is
    # worse than a visible error. The orchestrator's existing handler around
    # question_future.result() logs and recovers (see process_answer_in_background
    # and submit_answer_and_advance). Let the exception propagate there.
    result = call_tool(
        model=settings.LLM_MODEL,
        max_tokens=512,
        system=system,
        user_content=user_content,
        tool=_GENERATE_QUESTION_TOOL,
    )

    result["difficulty"] = experience_level
    result["question_type"] = question_type
    result["source_context"] = retrieval["context_text"][:1500]
    result["sources"] = retrieval["sources"]
    return result


def evaluate_answer(
    question: str,
    answer: str,
    context: str,
    experience_level: str,
    role: str = "",
    stance: str = "rigorous",
) -> dict:
    """
    Evaluates a candidate's answer against the role's rubric.

    `stance` varies the grading posture between the two independent passes in
    evaluate_answer_with_consistency (below) — using the exact same prompt twice
    would just reproduce the same output at near-zero variance and tell us
    nothing about how confident the grade actually is.

    Returns {score, dimension_scores, rubric_version, rationale, strengths, gaps}.
    `score` is a Python-computed weighted sum of dimension_scores — never a
    number the model invents holistically.
    """
    rubric = get_rubric(role)
    tool = _build_evaluate_answer_tool(rubric)

    rubric_text = "\n".join(f"- {d['label']} (weight {d['weight']}): {d['description']}" for d in rubric)
    stance_text = {
        "rigorous": "Be fair but rigorous. Do not give credit for confident-sounding but vague answers.",
        "lenient_check": (
            "Score independently and honestly. Give credit for correct reasoning even if phrasing is "
            "imperfect, but do not inflate scores for answers that are actually wrong or evasive."
        ),
    }.get(stance, "Be fair but rigorous.")

    # Static across every evaluate_answer call in a session — cached.
    system = f"""You are evaluating a technical interview answer using a fixed rubric. {stance_text}

Score EACH dimension independently on its own 0-10 scale:
{rubric_text}

Do not let a high score on one dimension inflate another. A vague-but-confident
answer should score low on correctness and depth even if communication is clear."""

    user_content = f"""Question: {question}

Expected knowledge context:
{context[:1500]}

Candidate's answer:
\"\"\"{answer[:1000]}\"\"\"

Candidate level: {experience_level}"""

    # No fake neutral fallback score on failure — a candidate's grade should never
    # come from a masked error. call_tool/create_message raise on failure, which
    # the caller (interview_orchestrator -> API layer) surfaces as a 500 to retry.
    result = call_tool(
        model=settings.LLM_MODEL,
        max_tokens=512,
        system=system,
        user_content=user_content,
        tool=tool,
    )

    missing = [d["key"] for d in rubric if d["key"] not in result]
    if missing:
        # A dimension score silently defaulting to 0 would drag the candidate's
        # weighted score down for a provider/schema hiccup, not a real evaluation
        # — the same failure mode the "no fake fallback score" policy above exists
        # to prevent. Fail loudly instead so the caller retries.
        raise ValueError(f"evaluate_answer: tool response missing required rubric dimensions: {missing}")

    dimension_scores = {d["key"]: result[d["key"]] for d in rubric}
    return {
        "score": weighted_score(dimension_scores, rubric),
        "dimension_scores": dimension_scores,
        "rubric_version": RUBRIC_VERSION,
        "rationale": result.get("rationale", ""),
        "strengths": result.get("strengths", ""),
        "gaps": result.get("gaps", ""),
    }


def evaluate_answer_with_consistency(
    question: str, answer: str, context: str, experience_level: str, role: str = ""
) -> dict:
    """
    Runs two independent rubric evaluations of the same answer — same rubric,
    deliberately different grading stance/phrasing — and compares their weighted
    scores. Large disagreement between two honest readings of the same rubric is
    itself a signal: either the answer is genuinely borderline, or the model's
    per-call judgment is noisy for this case. Either way, a human should look
    at it rather than silently trusting whichever pass happened to run first.

    Returns evaluate_answer's normal shape plus `score_variance` and
    `needs_human_review`. The primary evaluation's score/rationale/strengths/gaps
    are used as the answer's recorded values.
    """
    with ThreadPoolExecutor(max_workers=2) as pool:
        primary_future = pool.submit(evaluate_answer, question, answer, context, experience_level, role, "rigorous")
        check_future = pool.submit(evaluate_answer, question, answer, context, experience_level, role, "lenient_check")
        primary = primary_future.result()
        check = check_future.result()

    variance = round(abs(primary["score"] - check["score"]), 2)
    primary["score_variance"] = variance
    primary["needs_human_review"] = variance > CONSISTENCY_VARIANCE_THRESHOLD
    primary["consistency_check_score"] = check["score"]
    return primary


def generate_report(session_data: dict) -> dict:
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

    system = (
        "You are generating a hiring assessment report. Base the recommendation on: "
        "strong_yes (8+), yes (6.5-8), maybe (5-6.5), no (<5)."
    )

    user_content = f"""Candidate: {candidate.get("name", "Candidate")}
Role: {role.replace("_", " ").title()}
Experience level: {candidate.get("experience_level", "mid")}
Average score: {avg_score}/10

Interview transcript:
{qa_text[:4000]}"""

    try:
        return call_tool(
            model=settings.LLM_MODEL,
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


def _extract_topics_from_questions(questions: list[str]) -> list[str]:
    """Naive topic extraction from question text for de-duplication."""
    return questions  # The retriever uses these as negative signals via the prompt


def _determine_focus(previous_answer: str | None, previous_topics: list[str], question_number: int) -> str:
    """Determines focus area for retrieval based on session progress."""
    if question_number <= 2:
        return ""
    if previous_answer and len(previous_answer) < 80:
        return "fundamentals basics introduction"
    return ""
