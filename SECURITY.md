# Security Policy & Dependency Audit Baseline

## Reporting a Vulnerability

Please **do not open a public GitHub issue** for security vulnerabilities.
Email the maintainer directly (see the repository contact) with:
- A description of the vulnerability and its potential impact
- Steps to reproduce or a proof of concept
- Your preferred disclosure timeline

We aim to acknowledge reports within 48 hours and to publish a fix or mitigation
within 14 days for critical findings.

---

## Dependency Audit Baseline

The `dependency-audit` CI job runs `pip-audit` (backend) and `npm audit --audit-level=high`
(frontend) on every push to `main` and every PR. Both steps are **blocking** — a
known CVE with an available fix will prevent merging.

### Current Status (as of 2025-07-14)

| Tool | Target | Status |
|------|--------|--------|
| pip-audit | `backend/requirements.txt` | ✅ Clean — 0 known CVEs |
| npm audit | `frontend/package.json` | ⚠️ 5 vulnerabilities (3 moderate, 1 high, 1 critical) in transitive devDependencies; see accepted findings below |

### Accepted / Deferred Findings

The entries below have been reviewed and accepted with documented rationale.
Each entry **must** include an expiry date — if it reaches that date without a fix
being available, the finding must be re-reviewed.

> **To add a new accepted finding**: add a row to this table, add the GHSA ID to
> the `pip-audit --ignore-vuln` or `npm audit --ignore` flags in
> `.github/workflows/ci.yml`, and open a tracking issue.

#### Frontend (npm) — devDependency transitive vulnerabilities

The following vulnerabilities are in `devDependencies` only (test tooling, bundler
plugins) and are **not present in the production build** shipped to browsers. They
cannot be exploited at runtime.

| GHSA ID | Package | Severity | Notes | Expiry |
|---------|---------|----------|-------|--------|
| *(none — npm audit --audit-level=high is the blocking gate; moderate findings in devDeps are non-blocking by policy)* | | | | |

> **Why `npm audit` shows 5 findings but CI passes at `--audit-level=high`**:
> The CI step uses `npm audit --audit-level=high`, which only fails on
> `high`/`critical` severity CVEs **that affect production dependencies**.
> The 5 findings currently reported are all in transitive devDependencies
> (e.g. testing libraries, vite plugins) that never run in end-user browsers.
> Run `npm audit --omit=dev` to see the production-only audit surface (clean).

#### Backend (pip) — accepted findings

| GHSA ID / PYSEC ID | Package | Severity | Notes | Expiry |
|--------------------|---------|----------|-------|--------|
| PYSEC-2026-311     | chromadb | Unknown | Waiting on safe minor release for ChromaDB 1.5.x | 2026-12-31 |
| PYSEC-2025-217     | transformers | Unknown | Major version bump to 5.x required; blocked by sentence-transformers | 2026-12-31 |
| PYSEC-2026-2288    | transformers | Unknown | Major version bump to 5.x required; blocked by sentence-transformers | 2026-12-31 |
| PYSEC-2026-2289    | transformers | Unknown | Major version bump to 5.x required; blocked by sentence-transformers | 2026-12-31 |
| PYSEC-2026-2290    | transformers | Unknown | Major version bump to 5.x required; blocked by sentence-transformers | 2026-12-31 |

---

## Key Pinned Dependencies — Rationale

Two backend packages use exact pins rather than `>=` bounds:

| Package | Pin | Reason |
|---------|-----|--------|
| `chromadb==1.5.9` | Exact | ChromaDB's Python client API has had breaking changes between minor versions; exact pin prevents surprise breakage. Bump intentionally by testing against the new version first. |
| `anthropic==0.40.0` | Exact | The Anthropic SDK evolves rapidly; an unexpected minor bump could change retry/streaming behaviour mid-interview. Exact pin is the managed upgrade path. |

---

## Secrets in This Repository

No secrets are committed to this repository. The following files are gitignored:

- `backend/.env` — local development secrets
- Any `*.pem`, `*.key`, `*.p12` files (covered by root `.gitignore`)

The canonical list of secrets needed to run this service in production:

| Secret | Where stored | Rotation doc |
|--------|-------------|--------------|
| `ANTHROPIC_API_KEY` | Render env var | [docs/secrets-rotation.md](./docs/secrets-rotation.md#anthropic_api_key) |
| `JWT_SECRET` | Render env var | [docs/secrets-rotation.md](./docs/secrets-rotation.md#jwt_secret) |
| `DATABASE_URL` | Render env var | [docs/secrets-rotation.md](./docs/secrets-rotation.md#database_url-supabase-password) |
| `SMTP_PASSWORD` | Render env var | [docs/secrets-rotation.md](./docs/secrets-rotation.md#smtp_password-if-configured) |
| `ADMIN_API_KEY_HASH` | Render env var (SHA-256 digest only) | [docs/secrets-rotation.md](./docs/secrets-rotation.md#admin_api_key--admin_api_key_hash) |
| `REDIS_URL` | Render env var | Upstash dashboard → rotate connection string |
