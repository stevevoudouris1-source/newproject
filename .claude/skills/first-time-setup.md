# Skill: First-time setup

Run this **the first time you open an exec's fork** of the Turn 5 app starting
point. It is two short interviews, run conversationally, that capture who the
exec is and how their app should be wired. Do not freelance: ask the questions
below, write the files named below, commit with the messages named below.

The human you're talking to is a **non-technical Turn 5 executive**. You are the
only engineer. Be warm, plain-spoken, and ask one or two questions at a time —
never a wall of questions.

---

## Detection signals — is this a first session?

Check these before doing anything else:

1. **`ai_context/about_me.md` still holds the PLACEHOLDER** (it ships with a
   placeholder, not real content) → run **Interview A** (stakeholder onboarding).
2. **`setup_decisions.md` is ABSENT** (its absence is the signal — the file does
   not exist until the setup interview is done) → run **Interview B** (setup
   decisions).

If `about_me.md` is filled AND `setup_decisions.md` exists, setup is already
done. Skip this skill, read both files as background context, and continue with
whatever the exec asked for. Do not re-interview.

If only one signal fires, run only that interview.

> **The golden rule, repeated everywhere in this file:** secrets go **ONLY** in
> `.env` (gitignored). Never write a password, connection string with a
> password, or client secret into `about_me.md`, `setup_decisions.md`, a commit
> message, or any other tracked file. `.env.example` holds **keys only**, no
> values.

---

## Interview A — Stakeholder onboarding → `ai_context/about_me.md`

**Goal:** understand who this is and what they're building, so every later
recommendation is grounded. Ask 1–2 questions at a time, conversationally. Don't
move on until you've got a usable answer; it's fine to paraphrase back.

Ask, roughly in this order:

1. **Role / function** — "What's your role at Turn 5, and what team or function
   are you in (e.g. Finance, Ops, Sales, Marketplace)?"
2. **What the app is for + first feature** — "What are you trying to build? What's
   the problem it solves, and what's the very first thing you'd want it to do?"
3. **Audience** — "Roughly how many people will use this, and how technical are
   they? I'm assuming internal Turn 5 staff only — is that right?" (These apps are
   internal-only by design; confirm rather than assume.)
4. **Anything else** — "Anything else that helps me build the right thing —
   existing tools you'd want it to talk to, deadlines, or naming conventions you
   want me to follow?"

Then **write `ai_context/about_me.md`** as structured Markdown (headings + plain
prose). Replace the placeholder entirely. Suggested shape:

```markdown
# About me

## Who I am
- Role / title:
- Team / function:

## What this app is for
- Problem it solves:
- First feature:

## Audience
- Approx. number of users:
- Technical level:
- Internal-only: yes

## Notes
- Existing tools to integrate:
- Deadlines:
- Naming conventions:
```

**Commit** the change:

```
Capture stakeholder context
```

Tell the exec, at least once, that they can edit `ai_context/about_me.md`
directly any time, or just say "update my about-me with X" and you'll do it.

---

## Interview B — Setup decisions → `setup_decisions.md` + `.env`

**Goal:** wire the app to the right database, optional warehouse, and optional
SSO. This interview writes two things:

- **`setup_decisions.md`** — a **secret-free** summary of the choices made (which
  mode, warehouse yes/no, SSO yes/no, what's left to do). Tracked in git. No
  values, no passwords, no connection strings.
- **`.env`** — the real values (gitignored, local-only). This is the **only**
  place secrets go.

If `.env` doesn't exist yet, copy it from `.env.example` first (`.env.example`
holds keys only). Fill values in as you go.

Ask the three questions below, in order. Each has branching logic — follow it.

### B1. Prototype now, or real users now?

> "Are we prototyping first (I'll spin up a local database so you can see it
> working in minutes, zero setup), or are you putting real users on it right
> away?"

- **Prototyping (default, recommended to start)** → SQLite.
  - Set `MODE=prototype` in `.env`. That's it — the app uses
    `db/development.sqlite3` automatically, no connection details needed.
  - Note in `setup_decisions.md`: *"Database: SQLite (MODE=prototype). Switch to
    SQL Server when we go to real users."*

- **Real users now** → SQL Server.
  - Set `MODE=real` in `.env`.
  - Ask the exec for the **IT-provided connection details**: server host, port
    (usually 1433), database name, username, password.
  - Write them into `.env` **only**, as a single `DATABASE_URL`, using this exact
    SQL Server URL shape:
    ```
    DATABASE_URL=mssql://USER:PASSWORD@SERVER:1433/DBNAME?driver=ODBC+Driver+18+for+SQL+Server&Encrypt=yes&TrustServerCertificate=no
    ```
  - **Never** echo the password back in chat, in `setup_decisions.md`, or in a
    commit. In `setup_decisions.md` write only: *"Database: SQL Server
    (MODE=real). Connection details in .env (DATABASE_URL)."*

### B2. Warehouse access?

> "Do you need read-only access to the data warehouse (to pull in reporting data
> from elsewhere at Turn 5)?"

- **Yes** → ask IT for the warehouse connection details (same shape as above),
  and write them to `.env` **only**, as `WAREHOUSE_DATABASE_URL`. This becomes
  the read-only `warehouse` database alias.
  - In `setup_decisions.md`: *"Warehouse: enabled (read-only). Connection in .env
    (WAREHOUSE_DATABASE_URL)."*
- **No** → skip. Leave `WAREHOUSE_DATABASE_URL` unset.
  - In `setup_decisions.md`: *"Warehouse: not configured."*

### B3. Microsoft Entra SSO?

> "Do you want Turn 5 staff to sign in with their Microsoft / Entra accounts
> (single sign-on)? If you don't have the SSO details handy, we can skip it for
> now and add it later — the app still runs."

- **Yes, details available** → ask for the three Entra values and write them to
  `.env` **only**:
  ```
  OIDC_TENANT_ID=...
  OIDC_RP_CLIENT_ID=...
  OIDC_RP_CLIENT_SECRET=...
  ```
  (Endpoints are derived from the tenant automatically — login.microsoftonline.com
  and graph.microsoft.com/oidc/userinfo. You only need these three.)
  - In `setup_decisions.md`: *"SSO: Microsoft Entra configured. Secrets in .env."*

- **Not available / not now** → skip, and point the exec to
  **`.claude/skills/register-entra-app.md`** for how to register the app in Entra
  and get those three values when they're ready.
  - Explain plainly: the app **boots fine without OIDC**. Standalone
    username/password login is on by default (`PASSWORD_LOGIN_ENABLED`), so
    people can still sign in; set it to false to require SSO once configured.
  - In `setup_decisions.md`: *"SSO: not configured yet. See
    .claude/skills/register-entra-app.md. Password login on by default until
    then."*

### B4. Optional power tools (gstack)?

> "There's an optional set of 'power tools' (gstack) that give me extra abilities
> — clicking through your app in a real browser, automatically testing it and
> fixing bugs, reviewing how it looks, and digging into the root cause when
> something breaks. It's handy but not required. Want me to help you set them up
> now, or skip for now?"

- **Yes** → follow **`.claude/skills/power-tools.md`** to walk them through
  installing it via `/plugin`. In `setup_decisions.md`: *"Power tools: installed."*
- **Skip** → that's fine; they can ask any time later. In `setup_decisions.md`:
  *"Power tools: declined (offer again only if asked)."*

Either way, record the choice so future sessions don't re-ask.

### Write `setup_decisions.md` and commit

Assemble the secret-free summary. Suggested shape:

```markdown
# Setup decisions

- Database: <SQLite (MODE=prototype) | SQL Server (MODE=real), connection in .env>
- Warehouse: <enabled, connection in .env | not configured>
- SSO: <Entra configured | not configured yet — see register-entra-app.md>
- Power tools: <installed | declined>

## Notes / next steps
- <anything left to do>
```

Double-check there are **no secrets** in this file before saving. Then **commit**:

```
Record setup decisions
```

---

## After both interviews

1. Confirm `.env` has the right keys filled and is still gitignored (it is — never
   `git add` it).
2. Get the app running so the exec can see it. Typical first run:
   ```
   uv sync
   uv run python manage.py migrate
   uv run python manage.py tailwind build
   uv run python manage.py runserver
   ```
   The Claude admin account is provisioned by a data migration; if its password
   was set via `CLAUDE_ADMIN_PASSWORD` in `.env`, you can sign in with it.
3. Return to whatever the exec originally asked for, now with full context.

---

## Mention: who can reach the app (network allowlist)

Before you finish onboarding, **tell the exec this exists** (they don't have to
act on it now):

> "By default this app is reachable from anywhere you deploy it. If you ever want
> to lock it down to just the Turn 5 office or VPN — your intranet only — there's
> a plain-text file called `allowed_ips.txt` in the project. You (or I) can list
> the approved IP addresses there any time; until then it allows everyone."

Key points to convey:

- The file is **`allowed_ips.txt`** at the project root. Plain text, edit by hand.
- It ships allowing **all** traffic (a single `*`). Nothing is restricted by default.
- To restrict, replace `*` with office/VPN IPs or CIDR ranges (one per line).
- The `/up/` health check stays reachable regardless.
- In production behind a proxy, also set `IP_ALLOWLIST_TRUST_FORWARDED_FOR=true`
  in the environment so the real visitor's IP is checked.

If the exec already knows they want intranet-only access, offer to fill in
`allowed_ips.txt` now with the ranges their IT team provides.

---

## Reminders

- **Secrets live ONLY in `.env`.** If the exec asks you to "just put the DB
  password in `setup_decisions.md` so we remember it," refuse and explain it goes
  in `.env`. `.env.example` is keys-only.
- Ask **1–2 questions at a time**. Don't dump the whole list.
- These apps are **internal-only**. Confirm audience, don't assume scale.
- If a value isn't available yet (SQL Server creds, warehouse, SSO), it's fine to
  defer — note it in `setup_decisions.md` and move on. Prototype mode needs no
  setup at all.
