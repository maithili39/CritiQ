# CritiQ — AI-Powered Role-Based Candidate Screening System

Upload a resume, pick a role, and the system runs a full technical interview: the resume is
parsed, questions are generated one at a time from a role-specific knowledge base via RAG,
each answer is scored live, and a structured hiring report is produced at the end.

## Architecture

```
frontend/   React + Vite (TS, Tailwind, React Router) — upload UI, interview flow, report view
  src/pages/        route-level components (Home, InterviewSetup, Interview, Report)
  src/components/    shared UI (Navbar)
  src/context/        interview session state (React Context)
  src/lib/api.ts       typed fetch client for the backend API
backend/    FastAPI — sessions API, RAG pipeline, Claude orchestration
  app/api/         HTTP routes (sessions, admin)
  app/services/     resume parsing, question generation, interview orchestration
  app/rag/          ingestion (PDF -> chunks -> embeddings -> ChromaDB) + retrieval
  app/models/        SQLAlchemy models (sessions, questions, answers, reports)
  alembic/           Postgres schema migrations
  knowledge_base/   role-specific PDFs used as the RAG corpus
  data/              ChromaDB persistence (gitignored)
```

Flow: **resume upload → PDF text extraction → Claude resume parsing → RAG retrieval
(role + skills + domains) → Claude question generation → candidate answers → Claude
evaluation → repeat → Claude report generation**.

## Setup

### Backend

Requires a running Postgres instance (the quickest way is `docker-compose up postgres`,
or point `DATABASE_URL` at any Postgres you already have).

```bash
cd backend
python -m venv venv && venv\Scripts\activate   # or source venv/bin/activate on macOS/Linux
pip install -r requirements.txt
cp .env.example .env   # fill in ANTHROPIC_API_KEY, DATABASE_URL, and JWT_SECRET
alembic upgrade head   # create the schema
python ingest.py --role all   # ingest knowledge_base PDFs into ChromaDB
uvicorn app.main:app --reload
```

Backend runs on `http://localhost:8000`.

When you change a SQLAlchemy model, generate a new migration with:
```bash
alembic revision --autogenerate -m "describe the change"
alembic upgrade head
```

Run the backend test suite (in-memory SQLite, no live Postgres or Anthropic key needed —
every Claude call is mocked):
```bash
pip install -r requirements-dev.txt
pytest                              # add --cov=app --cov-report=term-missing for coverage
```

### Frontend

```bash
cd frontend
npm install
cp .env.example .env   # VITE_API_URL=http://localhost:8000/api
npm run dev
```

Frontend runs on `http://localhost:3000`. `npm run build` typechecks and produces a static
`dist/` bundle; `npm run preview` serves it locally.

Run the frontend test suite (Vitest + React Testing Library):
```bash
npm run test          # single run
npm run test:watch    # watch mode
```

### Docker

```bash
docker-compose up --build
```

## Key design decisions

- **RAG grounding, not hallucinated questions**: every question is generated from chunks
  retrieved from role-specific textbooks (ChromaDB + sentence-transformers embeddings),
  not from the model's parametric knowledge alone.
- **Recursive chunking** (paragraph → sentence → word, 512 chars / 64 overlap) preserves
  semantic boundaries better than fixed-size splitting.
- **Query construction** combines the candidate's parsed skills/technologies/domains with
  the selected role, and steers away from topics already covered earlier in the interview.
- **One question at a time**, not a batch — each question can adapt to the previous answer
  (deeper follow-up on strong answers, fundamentals check on weak ones).
- **Full traceability**: each stored question keeps the exact retrieved context it was
  grounded in (`source_context`), so every question can be traced back to its source chunks.
- **Session state machine** (`created → active → completed`) lives in
  `interview_orchestrator.py` as the single source of truth, kept independent of the API
  layer so it's testable without HTTP.

## Production readiness

Hardened so far:
- **Postgres**, not SQLite — handles real concurrent writers, and is the same engine
  you'd run in production. `docker-compose.yml` runs it as a service with a health check
  so the backend waits for it to be ready before starting.
- **Alembic migrations** — schema changes are versioned (`backend/alembic/versions/`)
  instead of relying on `create_all`, which can only add tables, never alter them.
- Indexes on all foreign key columns (`session_id`, `question_id`) to avoid full table
  scans as data grows.
- Rate limiting (`slowapi`) on every endpoint that triggers a Claude API call, to protect
  against abuse and runaway API cost.
- Input validation on candidate name/email/answer length; API error responses no longer
  leak raw exception strings to the client (logged server-side instead).
- **User accounts** — email/password signup ([backend/app/api/auth.py](backend/app/api/auth.py)),
  passwords hashed with `bcrypt`, sessions authenticated via a JWT bearer token
  (`Authorization: Bearer <token>`, 7-day expiry). Every `InterviewSession` belongs to a
  `user_id`; `require_owned_session` in [backend/app/api/sessions.py](backend/app/api/sessions.py)
  checks the logged-in user against `session.user_id` on every session-scoped endpoint,
  and 404s (not 403) on a mismatch so an attacker can't distinguish "not yours" from
  "doesn't exist." `GET /sessions` lists everything the current user has created — the
  frontend's "My Sessions" page — so screenings are visible from any device you log in
  from, not just the browser that started them.
- **Automated backups** — `docker-compose.yml` runs a `backup` service (built from
  [backend/scripts/backup-cron/Dockerfile](backend/scripts/backup-cron/Dockerfile)) on a
  cron schedule (`backend/scripts/backup-cron/crontab`, daily at 02:00 by default), calling
  `backup.sh` to `pg_dump` (custom format) plus tar the ChromaDB persistence dir into
  `backend/backups/<timestamp>/`. `backup.sh`/`.ps1` and `restore.sh`/`.ps1` also work
  standalone (outside Docker) if you're running Postgres elsewhere.
- **Password reset & email verification** — token-based flows in
  [backend/app/api/auth.py](backend/app/api/auth.py) (`/auth/password-reset/*`,
  `/auth/verify-email/*`); tokens are hashed at rest, single-use, and time-limited.
  Emails send via SMTP when configured, otherwise log a warning so local dev doesn't
  need real infrastructure.
- **Account lockout** — `AUTH_MAX_FAILED_ATTEMPTS` wrong passwords locks the account for
  `AUTH_LOCKOUT_MINUTES` (both configurable), independent of the general IP-based rate limit.
- **Admin endpoints require `X-Admin-API-Key`** — `/api/admin/*` is gated behind
  `require_admin_api_key`; disabled entirely (503) until `ADMIN_API_KEY` is set.
- **PDF upload validated by content, not just filename** — resumes are checked for the
  `%PDF-` magic bytes, not just a `.pdf` extension, before being parsed.
- **CORS allowlist is env-driven** (`ALLOWED_ORIGINS`), not hardcoded to localhost.
- **Automated tests** — `backend/tests/` (pytest, in-memory SQLite, Claude calls mocked)
  covers auth, session-ownership (regression test for the cross-user access bug fixed
  earlier), the full interview flow, and the orchestrator directly. `frontend/src/**/*.test.ts(x)`
  (Vitest + React Testing Library) covers the API client, auth context, and route
  protection. Both run in CI-friendly single-shot mode with no external services required.
- **CI** — `.github/workflows/ci.yml` runs the backend pytest suite and the frontend
  Vitest suite + typecheck/build on every push and PR to `main`.
- **Structured LLM output** — resume parsing, question generation, answer evaluation, and
  report generation all use Claude tool-use with a forced `tool_choice` (see
  [backend/app/services/llm.py](backend/app/services/llm.py)), so responses are
  guaranteed to match a JSON schema instead of being parsed out of free-form text/markdown
  fences. A failed evaluation call raises rather than silently awarding a neutral score.
- **Retries + prompt caching** — every Claude call goes through `create_message` /
  `call_tool` in `llm.py`: transient failures (429/5xx/timeout/connection) retry with
  exponential backoff; the repeated system-prompt instructions in `generate_question` and
  `evaluate_answer` (called ~`MAX_QUESTIONS` times per session) are marked
  `cache_control: ephemeral` to cut repeated input-token cost.
- **Error tracking** — Sentry wired in `app/main.py`, enabled by setting `SENTRY_DSN`;
  logging can switch to structured JSON (`LOG_JSON=true`) for log aggregators.
- **Two-sided recruiter/candidate flow** — creating a session ([backend/app/api/sessions.py](backend/app/api/sessions.py))
  returns an `invite_url` (`/take/{session_id}?token=...`) built from a per-session
  `access_token`; the recruiter can copy it, email it via `/sessions/{id}/invite/send`,
  or preview the interview themselves. The candidate takes the interview at that link
  with no account, authenticated only by the token
  ([backend/app/api/candidate.py](backend/app/api/candidate.py),
  [frontend/src/pages/CandidateInterview.tsx](frontend/src/pages/CandidateInterview.tsx)).
  The candidate-facing API deliberately omits per-answer scores, rationale, and the
  final report — those are the recruiter's hiring judgment, not the candidate's to see
  live (it would let them game later answers) or at all.

- **Knowledge base auto-ingests on startup** — the backend `CMD` runs `python ingest.py
  --role all` before `uvicorn` starts. `ingest_role_documents` is idempotent (skips a
  role's collection if it's already populated), so this is safe on every restart —
  no manual one-time step to remember on a fresh deployment, which previously meant an
  empty ChromaDB and silently ungrounded interview questions with no error surfaced.
- **Rate limiting scales horizontally** — `REDIS_URL` switches `slowapi`'s storage from
  in-memory (fine for one container) to Redis (required once you run more than one
  backend replica, so limits are enforced globally instead of separately per replica).
  `docker-compose.yml` includes a `redis` service wired up by default.
- **Rate limiter sees the real client IP behind a proxy** — `uvicorn --proxy-headers
  --forwarded-allow-ips='*'` rewrites `request.client.host` from `X-Forwarded-For`, so
  `get_remote_address` isn't just reading your load balancer's IP for every request.
- **Frontend API URL is a runtime setting, not baked into the build** —
  `docker-entrypoint.sh` writes `/config.js` (`window.__API_BASE__`) from the `API_BASE`
  env var when the container starts, not at `docker build` time. The same built image
  can move between environments (staging → prod) by changing the env var and
  restarting, with no rebuild.
- **`create_session` no longer blocks the whole event loop** — it's an `async def`
  endpoint, but was calling the blocking `orchestrator.create_session` (PDF parsing,
  embeddings, a synchronous Anthropic API call) directly with no `await`, which froze
  the entire process for every concurrent request during that call, not just this one.
  Now offloaded via `run_in_threadpool`, matching how FastAPI already auto-threadpools
  the other (plain `def`) endpoints.
- **`app/rag/` has real unit tests** — `tests/test_rag_ingestion.py` and
  `tests/test_rag_retriever.py` test the chunking/overlap logic and the
  relevance-scoring/filtering math directly (ChromaDB and the embedding model stubbed),
  not just indirectly through orchestrator mocks. Writing them caught a real bug: the
  character-split fallback path in `_recursive_split` was double-applying overlap
  (once via its stride, once via an unconditional tail-prepend afterward), inflating
  chunks past `chunk_size` — fixed in the same change.
- **Backup/restore has an automated drill** — `scripts/backup_restore_drill.sh` seeds a
  marker row, runs `backup.sh`, destroys the database (`DROP SCHEMA public CASCADE`) to
  prove restore isn't a no-op, runs `restore.sh`, and asserts the marker row came back.
  Wired into CI (`.github/workflows/ci.yml`) against a real throwaway Postgres service
  container — this is a genuine dump → destroy → restore round-trip, not a mock.

- **Answer scoring and next-question generation now run concurrently** —
  `orchestrator.submit_answer_and_advance` replaces the old sequential
  `submit_answer` then `get_next_question` calls with two Claude requests fired at
  once via `ThreadPoolExecutor`. They're independent (next-question generation only
  needs the raw answer text, not its score), so this roughly halves the latency a
  candidate feels between submitting one answer and seeing the next question — a
  real, scoped fix, not the full background-job-queue rewrite that would be needed to
  remove request/response waiting entirely (see below for what that would still take).

Known limitations (not yet addressed):
- Only two role tracks are wired up (`ai_ml`, `data_science`), hardcoded in three places
  (backend `ALLOWED_ROLES`, frontend role labels, and the Home page).
- The candidate still waits on the same HTTP request/response cycle for scoring +
  next-question generation (now parallelized, see above, but not eliminated). Removing
  that wait entirely — return immediately, deliver the next question over
  websocket/polling once ready — is a real architecture change (a job queue, a
  "pending" state in the schema, a frontend poll loop), not a one-line fix. Worth doing
  once concurrent interview volume is high enough that ~halved latency isn't enough.
- No ATS integrations, team workspaces, or billing — single recruiter accounts only.
  These are genuine multi-week product features, not something to bolt on as a "fix" —
  worth scoping as their own dedicated phase when you're ready to prioritize one.
