---
name: graduate-sqlite-to-sqlserver
description: Migrate this app from MODE=prototype (SQLite) to MODE=real (SQL Server). Use when the prototype is ready for real, shared, durable data or when Turn 5 IT has provisioned a SQL Server database for the app.
---

# Graduate SQLite -> SQL Server

You built and proved the app in **prototype mode** (zero-setup SQLite at
`db/development.sqlite3`). This skill moves it to **real mode** (SQL Server)
without losing the data you already created.

## When to run this

- The prototype works and people want to start using it for real.
- Turn 5 IT has (or will) hand you a per-user SQL Server connection.
- You need the data to be shared, backed up, and durable.

If you're still experimenting, stay in prototype mode. SQLite is the default for
a reason — nothing to set up, nothing to break.

## Before you start

- **VPN:** If you're off the Turn 5 network, connect to the VPN first. SQL Server
  is not reachable from the public internet.
- **ODBC Driver 18:** The SQL Server connection needs Microsoft ODBC Driver 18
  for SQL Server installed on this machine. See `ai_context/setup.md` for the install
  link and steps. Without it, `migrate` will fail to connect.
- **A backup mindset:** This is a copy-forward, not a destructive move. Your
  SQLite file stays untouched. If anything looks wrong, you can stop and you've
  lost nothing.

---

## Steps

### 1. Snapshot the prototype data

While still in prototype mode (SQLite), export everything to a portable file:

```
uv run python manage.py dumpdata --natural-foreign --natural-primary --exclude contenttypes --exclude auth.permission > snapshot.json
```

- `--natural-foreign --natural-primary` make foreign keys portable across
  databases instead of hard-coding SQLite's auto-increment IDs.
- We exclude `contenttypes` and `auth.permission` because Django regenerates
  those from your models during `migrate` — re-loading them would collide.

`snapshot.json` now holds your users, permission grants, and app data.

### 2. Get the SQL Server connection from Turn 5 IT

Turn 5 IT issues a **per-user** SQL Server connection (your own login, not a
shared one). Ask them for it. Confirm ODBC Driver 18 is installed
(`ai_context/setup.md`).

### 3. Point `.env` at SQL Server

Edit `.env` (never a tracked file — `.env` is gitignored). Set:

```
MODE=real
DATABASE_URL=mssql://USER:PASSWORD@SERVER:1433/DBNAME?driver=ODBC+Driver+18+for+SQL+Server&Encrypt=yes&TrustServerCertificate=no
```

Use the exact URL IT gave you. The `driver=`, `Encrypt=yes`, and
`TrustServerCertificate=no` parameters matter — keep them. Put the real
credentials **only in `.env`**, never in `.env.example`, never in a commit,
never in a doc.

> Optional read-only warehouse: if IT also gives you a warehouse connection, set
> `WAREHOUSE_DATABASE_URL` (DB alias `warehouse`). Not required to graduate.

### 4. Build the schema on SQL Server

Run migrations against the empty SQL Server database:

```
uv run python manage.py migrate
```

This creates every table from your models. The database should be empty/new —
let Django build it from scratch.

### 5. Load the snapshot

```
uv run python manage.py loaddata snapshot.json
```

This replays your prototype data into SQL Server. Watch for errors here — see
**Field-type gotchas** below if a load fails.

### 6. Restore the Claude admin account and verify

The snapshot may not carry a usable password for the Claude admin service
account (the password lives only in env, never in data). Re-establish it:

- Set `CLAUDE_ADMIN_PASSWORD` in `.env`.
- Re-run the provisioning so the account is correct on the new database:
  ```
  uv run python manage.py migrate
  ```
  The data migration `apps/accounts/migrations/0002_provision_claude_admin.py`
  provisions `claude@turn5.local` idempotently. If you prefer a fresh secret,
  rotate it: `uv run python manage.py rotate_claude_password` (prints a 32-char
  password once).
- Verify login works:
  - Sign in at `/accounts/login/` with the Claude service account (or any user
    with password login on), or via Entra SSO if it's configured.
- Run the full check suite to confirm the app is healthy on SQL Server:
  ```
  bin/ci
  ```

If login works and `bin/ci` is green, you've graduated.

---

## Field-type gotchas

SQLite is permissive; SQL Server is strict. Data that looked fine in prototype
can surface problems on load. Test thoroughly — open the app, click through real
flows, don't just trust a green migrate.

- **SQLite is lax, SQL Server is strict.** SQLite stores almost anything in any
  column; SQL Server enforces types, lengths, and null rules. A string that
  overflowed a column or a stray null can pass in prototype and fail on
  `loaddata`. If a load errors, the message usually names the model/field —
  start there.
- **`DateTimeField` precision.** SQL Server and SQLite store fractional seconds
  differently; microseconds can round or shift slightly. Don't write tests or
  logic that assume exact-microsecond equality across the two databases.
- **`JSONField`** works on both backends — no special handling needed.
- **`BooleanField` and auto fields.** Booleans map to a real bit type on SQL
  Server (not 0/1 integers as in SQLite); auto-increment / identity columns are
  handled by SQL Server's identity mechanism. The natural-key flags in step 1
  keep relationships intact, but spot-check that boolean flags
  (e.g. `is_claude_service`) and IDs survived the round trip.

When something looks off, it's almost always a type/length/null mismatch the
strict backend caught — fix the source data or the field definition, re-snapshot
(step 1), and reload.

---

## Rolling back

Nothing here is destructive to your prototype. To return to SQLite, set
`MODE=prototype` in `.env` (and clear `DATABASE_URL` if you like) — your
`db/development.sqlite3` is exactly as you left it.
