# Security

The defense-in-depth guardrails this template ships with, and where each lives.
Read this before changing anything security-sensitive; **never weaken a guardrail
without telling the user** (CLAUDE.md → Operating principles). Auth/authz has its
own doc — see [auth.md](auth.md).

## Key files

| File | Role |
|---|---|
| `allowed_ips.txt` | Plain-text IP/CIDR allowlist (repo root, user-editable) |
| `apps/common/ip_allowlist.py` | `IPAllowlistMiddleware` that enforces it |
| `config/settings/base.py` | CSP, password validators, allowlist + secret config |
| `config/settings/prod.py` | Production hardening (HTTPS, secure cookies, HSTS) |
| `apps/accounts/views.py` | Login rate-limiting (`@ratelimit`) |
| `tests/test_guardrails.py` | Tests for rate limit, CSP, allowlist |
| `.env` / `.env.example` | Where secrets live (never committed) |

## IP allowlisting (whitelisting)

The app can be restricted to approved client IPs via the plain-text
**`allowed_ips.txt`** at the repo root, enforced by `IPAllowlistMiddleware`
(`apps/common/ip_allowlist.py`), which runs **early in the middleware stack** so
blocked IPs never reach app logic.

- **Default is allow-all.** A file containing `*` (or only comments/blanks, or no
  file at all) lets everyone through. Teams lock down by listing IPs or CIDR
  ranges, one per line (`#` comments allowed).
- **Live reload.** The file is re-read whenever its mtime changes — edit it, no
  redeploy. Bad lines are skipped rather than taking the app down.
- **`/up/` is always exempt** so load balancers can health-check.
- **Behind a proxy:** set `IP_ALLOWLIST_TRUST_FORWARDED_FOR=true` so the real
  client IP (first `X-Forwarded-For` entry) is checked instead of the proxy's.
  Only enable behind a trusted proxy. Configurable file path via
  `IP_ALLOWLIST_FILE` (defaults to `allowed_ips.txt`).

## Rate limiting

`django-ratelimit` caps the login endpoint at **5 POST/min/IP** (and the OIDC
callback at 5/min/IP) — brute-force protection on `RateLimitedLoginView`. Toggled
by `RATELIMIT_ENABLE` (off in tests except the dedicated rate-limit test, which
freezes the clock to avoid a window-boundary flake — see [auth.md](auth.md)).

## Content-Security-Policy

`django-csp` sets a **report-only** policy (`CONTENT_SECURITY_POLICY_REPORT_ONLY`
in base.py): `default-src 'self'`, `frame-ancestors 'none'`, `object-src 'none'`,
etc. Report-only logs violations without breaking anything; Phase 3 promotes it to
enforced (and drops Alpine's `eval()` need via its CSP build / nonces). Don't
weaken it without asking.

## Secrets

- **Never commit credentials.** Secrets live in `.env` (gitignored, local) or
  platform env vars / Azure Key Vault in prod — never in tracked files. See
  CLAUDE.md → Security for the full routing rules. If asked to "just put it in
  CLAUDE.md/README for now," refuse and redirect.
- `SECRET_KEY` has a dev-insecure default in base.py; **prod.py requires it from
  the environment** (fails to boot otherwise).
- `CLAUDE_ADMIN_PASSWORD` has no default — read from the environment by the
  provisioning migration.
- Password strength: `AUTH_PASSWORD_VALIDATORS` (min length 12, common, numeric,
  similarity).

## Other guardrails

- **CSRF** on all forms (Django default); don't disable it.
- **Mass-assignment:** never expose `role`, `is_staff`, `is_superuser`,
  `is_claude_service`, or permissions in a user-facing form (see [auth.md](auth.md)).
- **Deny-by-default auth/authz** — see [auth.md](auth.md).
- **Production hardening** (`prod.py`): `DEBUG=False`, `SECURE_SSL_REDIRECT`,
  secure + HTTPOnly cookies, HSTS (1y, preload, subdomains),
  `SECURE_CONTENT_TYPE_NOSNIFF`, `X_FRAME_OPTIONS=DENY`,
  `SECURE_PROXY_SSL_HEADER` (HTTPS terminated at the platform).

## Related

- `CLAUDE.md` → Security, Network access (IP allowlist).
- [auth.md](auth.md) — authentication & authorization.
- `CHANGELOG.md` — change history.
