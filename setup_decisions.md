# Setup decisions

_Recorded 2026-11-15. Secret-free summary — actual values live only in `.env`._

- **Database:** SQLite (`MODE=prototype`). Switch to SQL Server later via
  `.claude/skills/graduate-sqlite-to-sqlserver.md`.
- **Warehouse:** not configured (not needed for the tour page).
- **SSO:** not configured yet. Users sign in with username/password. See
  `.claude/skills/register-entra-app.md` when ready.
- **Power tools:** offered, not installed (the user can ask any time).
- **Network allowlist:** `allowed_ips.txt` still allows all traffic (default).
