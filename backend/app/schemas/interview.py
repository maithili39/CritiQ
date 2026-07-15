from pydantic import BaseModel, Field


class AnswerSubmit(BaseModel):
    answer_text: str

    # --- Anti-cheating telemetry (all optional — graceful degradation if the
    # browser doesn't support a specific API or the user denied camera access) ---

    # Milliseconds from question display to answer submission, measured client-side.
    response_time_ms: int | None = Field(default=None, ge=0)

    # True if a paste event was detected in the answer textarea.
    paste_detected: bool | None = None

    # How many times the candidate switched away from the tab/window.
    tab_switch_count: int | None = Field(default=None, ge=0)

    # Base64-encoded JPEG webcam still captured at submission time.
    # Stored as-is; size is bounded on the client (JPEG at 0.4 quality ~20-40 KB).
    camera_snapshot: str | None = None


class OutcomeSubmit(BaseModel):
    # Real post-interview hiring outcome recorded by the recruiter (ground truth).
    outcome: str = Field(..., pattern=r"^(rejected|no_show|hired|hired_strong)$")
    note: str | None = Field(default=None, max_length=1000)


class CustomRoleCreate(BaseModel):
    slug: str = Field(
        ...,
        min_length=2,
        max_length=100,
        pattern=r"^[a-z0-9_]+$",
        description="Lowercase slug, letters/digits/underscores only (e.g. 'backend_engineer')",
    )
    label: str = Field(..., min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=500)
    topics: list[str] = Field(default_factory=list)

    # Optional: recruiter-supplied interviewer persona / difficulty guidance. If
    # omitted, both are LLM-generated from label/description/topics at creation
    # time so the role still drives question generation like a built-in one.
    persona: str | None = Field(default=None, max_length=1000)
    difficulty_guide: str | None = Field(default=None, max_length=2000)
