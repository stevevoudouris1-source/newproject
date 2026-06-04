# Turn 5 App Starting Point

A ready-to-build starting point for internal Turn 5 apps — a dashboard, a workflow tool, a record-keeper. You build it by **talking to Claude Code** (Anthropic's coding AI) in plain English. The template gives Claude the rails to stay on, so whatever it builds is secure, fast, and maintainable by default.

## Who this is for

You — a Turn 5 exec who wants an internal app but doesn't want to learn to write code. You describe what you need; Claude builds it. You don't have to understand the stack below to use this.

## Quick start

1. **Make it yours.** You've already clicked **"Use this template"** — you now have your own private repo.
2. **Set up your computer.** Follow `ai_context/setup.md` (Mac or Windows), step by step.
3. **Open the repo with Claude Code and tell it what you want to build.**

The first time Claude opens your repo, it runs two short interviews automatically — an onboarding interview (about you and your team) and a setup interview (about the app). You just answer in plain English. The playbook Claude follows is `.claude/skills/first-time-setup.md`; your answers are saved so future sessions remember.

## How to ask Claude for things

Describe what you want in everyday language. For example:

- "Add an Invoice with a customer, an amount, and a due date. Only admins can delete them."
- "Show me a list of all customers with a search box. Make sure it's fast even with 50,000 of them."
- "Anyone with the manage_invoices permission should be able to mark an invoice as paid."

Claude will ask questions if anything's unclear, write tests, build the feature, run the checks, and then show you the result before saving. If something feels off, say so — Claude can undo it and try again.

## You don't need to learn git

Your app has a built-in **time machine**. Every change Claude makes is saved and
backed up to the cloud automatically — you never have to think about "version
control," and you never need to type a single git command.

Just talk to Claude in plain English:

- **"save my work"** — saves a checkpoint and backs it up (Claude also does this
  automatically after each change).
- **"undo that"** — reverses the last change.
- **"go back to yesterday's version"** — restores an earlier version.
- **"what changed?"** — Claude tells you, in plain English.

Nothing is ever lost: going back always moves *forward* to an earlier state, so
your history stays intact.

## The Claude admin account

There's a built-in admin account so Claude can sign in and use the app like a real user:

- **Username / email:** `claude@turn5.local`
- **Password:** lives only in your `.env` file (never in the code, never in chat).
- **Sign in at:** `/accounts/login/`

This account always works. Beyond it, **standalone username/password login is on by default** (`PASSWORD_LOGIN_ENABLED`), so you can create real user accounts and have people sign in before — or instead of — setting up Microsoft sign-in. Admins set passwords from the Users page; everyone can change their own. Turn password login off (and rely solely on Entra SSO) by setting `PASSWORD_LOGIN_ENABLED=false` once SSO is configured.

## The stack at a glance

You don't need to know any of this — Claude handles it — but here's what's under the hood:

- **Django 5** (Python) — the app framework
- **Database** — SQLite to start (zero setup), or SQL Server when you go to real data
- **Microsoft sign-in** — Entra SSO, so your team logs in with their work accounts
- **Tailwind + HTMX + Alpine** — modern, fast UI, **with no Node/npm to install**
- **pytest** (tests), **Ruff** (code style), **uv** (the tool that runs everything)

## Running it after setup

Once `ai_context/setup.md` is done:

```
bin/setup
uv run python manage.py runserver
```

Then open the address it prints (usually http://127.0.0.1:8000). Sign in with the Claude admin account above.

## Working solo vs. with a team

By default you work **solo on one place — your live app** — and Claude saves and
backs up every change for you. No branches, no pull requests, nothing extra to
track. This is the simplest way to work, and what we recommend to start.

If a **second person** starts helping, just ask Claude to switch you to a team
setup — it'll turn on "review requests" (so changes are checked before they go
live) and branch protection on GitHub. You don't need any of that until someone
else is in the codebase.

## Optional: power tools

There's an optional add-on called **gstack** — a set of Claude Code skills that
give Claude extra abilities: clicking through your app in a real browser
(`/browse`), automatically testing it and fixing bugs (`/qa`), reviewing how it
looks (`/design-review`), and digging into the root cause when something breaks
(`/investigate`).

It's **optional** and not installed by default. On your first session, Claude
will ask if you'd like to set it up — say yes and Claude walks you through it, or
skip it and ask later. (It installs through Claude Code's plugin marketplace,
separately from this app.)

One note: gstack also includes tools that can deploy or publish code. Claude is
instructed to treat those with the same care as everything else here — asking you
first and respecting your protected `main` branch.

## Where to look next

- **`CLAUDE.md`** — the house rules Claude reads at the start of every session.
- **`ai_context/setup.md`** — full, step-by-step setup for your computer.

That's it. Open the repo with Claude, tell it what you want, and go.
