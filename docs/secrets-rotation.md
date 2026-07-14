# Secrets rotation runbook

Internal ops reference for rotating each secret this project depends on, without
unplanned downtime or locking out users. Not part of the public README — this is
for whoever operates the deployment, not for someone evaluating the project.

---

## JWT_SECRET

**Impact of rotating:** every existing login token is signed with the old secret.
The moment you deploy a new `JWT_SECRET`, all currently logged-in users are signed
out on their next request (`decode_access_token` fails to verify) and must log in
again. There is no way to rotate this without that side effect — the token itself
has no versioning field to support a grace period.

**When to rotate:** the secret is suspected leaked (e.g. it appeared in a log, a
screen share, a committed `.env`), or on a routine schedule (e.g. every 90 days)
if your security policy calls for it.

**Steps:**
1. Generate a new secret: `python -c "import secrets; print(secrets.token_urlsafe(48))"`
2. Set it as `JWT_SECRET` in Render's environment variables and deploy
3. Expect a burst of re-logins immediately after — this is expected, not a bug
4. Old tokens are now permanently invalid; nothing further to clean up

---

## ANTHROPIC_API_KEY

**Impact of rotating:** none to end users if done correctly — this key isn't
tied to any user session, so replacing it takes effect on the next Claude call
with zero downtime.

**When to rotate:** suspected leak, or as part of routine key hygiene.

**Steps:**
1. In the Anthropic Console, create a new API key (don't revoke the old one yet)
2. Set the new key as `ANTHROPIC_API_KEY` in Render and deploy
3. Confirm the app works (create a session, generate a question) with the new key
4. Only after confirming, revoke the old key in the Anthropic Console

---

## DATABASE_URL (Postgres)

**Impact of rotating:** brief connection errors for in-flight requests during the
window between resetting the password and updating `DATABASE_URL`.

**Steps (Render-managed Postgres):**
If you deployed using the included `render.yaml` blueprint, Render manages the
Postgres instance natively. You generally do not need to manually rotate the password.
If required, rotation is handled via the Render dashboard for the Postgres service,
and Render automatically updates the attached `DATABASE_URL` env var.

**Steps (External Supabase):**
If you chose to use an external Supabase instance instead of the blueprint default:
1. In Supabase: Project Settings → Database → **Reset password**
2. Immediately update `DATABASE_URL` in Render's environment variables with the
   new password (same host/port/pooler mode as before, only the password changes)
3. Redeploy on Render
4. Watch the deploy logs — a failed `alembic upgrade head` or connection error
   here means the new `DATABASE_URL` wasn't set correctly before redeploying

---

## SMTP_PASSWORD (if configured)

**Impact of rotating:** password-reset and email-verification emails silently
stop sending until updated (they log a warning and continue rather than crash,
so this fails quietly — check logs after rotating).

**Steps:**
1. Generate a new app password/API key with your email provider
2. Update `SMTP_PASSWORD` in Render and deploy
3. Trigger a real password-reset request to confirm delivery still works

---

## ADMIN_API_KEY / ADMIN_API_KEY_HASH

**Background:** the admin key protects `/api/admin/*` (knowledge-base ingest/rebuild).
Two storage modes exist — use whichever matches your current `render.yaml` setup:

### Preferred: ADMIN_API_KEY_HASH

Rotation is a single env-var update — the raw key never enters the running process.

**Impact of rotating:** any script/tool using the old key gets 403s immediately
after the new hash is deployed.

**Steps:**
1. Generate a new raw key:
   ```
   python -c "import secrets; print(secrets.token_urlsafe(48))"
   ```
2. Hash it (the hash is what gets stored, not the raw key):
   ```
   echo -n 'YOUR_NEW_RAW_KEY' | sha256sum
   ```
3. Set `ADMIN_API_KEY_HASH` in Render to the hex digest from step 2 and redeploy
4. Update any tooling that calls `/api/admin/*` to use the new raw key in the
   `X-Admin-API-Key` header

### Legacy: ADMIN_API_KEY (plaintext)

**Impact of rotating:** any script/tool using the old key gets 403s immediately.

**Steps:**
1. Generate a new random value: `python -c "import secrets; print(secrets.token_urlsafe(48))"`
2. Update `ADMIN_API_KEY` in Render and deploy
3. Update the key in any tooling that calls `/api/admin/*`

> **Migration from ADMIN_API_KEY → ADMIN_API_KEY_HASH**: set `ADMIN_API_KEY_HASH`
> to the SHA-256 hash of your new key, clear `ADMIN_API_KEY`, and deploy.
> `require_admin_api_key` in `app/api/deps.py` checks `ADMIN_API_KEY_HASH` first.

---

## REDIS_URL (Redis)

**Impact of rotating:** rate-limiting state is lost (counters reset) for the
window between the old URL being dropped and the new one being live. In practice
this is a brief window during a Render redeploy and results in no user-visible
behaviour — rate limits simply reset for a few seconds. Not a security concern.

**Steps (Render-managed Redis):**
If deployed via the included `render.yaml` blueprint, Render manages Redis natively.
Rotation is not typically required. If you delete and recreate the Redis service,
Render will automatically update the attached `REDIS_URL` in the backend service.

**Steps (External Upstash):**
If using an external Upstash Redis instance:
1. In the Upstash dashboard: select your Redis database → **Reset Password**
   (or create a new database if rotating entirely)
2. Copy the new connection string (starts with `rediss://`)
3. Update `REDIS_URL` in Render and trigger a redeploy
4. Confirm the backend starts cleanly (no Redis connection errors in the deploy log)

---

## General principle

For anything that *doesn't* invalidate live sessions (API keys, DB password,
SMTP, Redis, admin key), rotate in the **"new key first, verify, then revoke old
key"** order above — that's what makes it zero-downtime. `JWT_SECRET` is the one
exception where a brief mass-logout is unavoidable and expected.

If you suspect a widespread compromise (multiple secrets leaked simultaneously),
rotate `JWT_SECRET` last so you can confirm the app works after each other rotation
before invalidating all sessions.
