---
name: power-tools
description: Optional gstack power tools (browser QA, design review, root-cause debugging). Use when the user asks to install/set up the optional power tools, or on the first session when offering them.
---

# Skill: optional power tools (gstack)

**gstack** is an optional, third-party suite of Claude Code skills that adds
browser automation, QA, visual design review, and debugging workflows. This
template does **not** bundle it — it's an opt-in power-up, installed per-user
through the Claude Code plugin marketplace so it updates centrally and isn't
frozen into every app repo.

Offer it **once**, on the first session (see "First load" below). The template is
fully functional without it.

## Recommended skills (low-risk, exec-friendly)

These pair well with this template and are safe for non-technical users:

- **/browse** — drive a headless browser to click through and screenshot the app.
- **/qa** — systematically test the app and fix the bugs it finds.
- **/design-review** — a designer's-eye visual QA of the live UI.
- **/investigate** — structured root-cause debugging when something breaks.

gstack ships many more skills (shipping, deploys, security audits, retros, …).
They become available once installed — but read the cautions first.

## Cautions — keep the guardrails

Some gstack skills can deploy, merge, or force-push. They **must** respect this
project's rules in `CLAUDE.md`:

- Branch protection and ask-first still apply. Do not let `/ship`,
  `/land-and-deploy`, or any merge/deploy skill bypass a required PR + green CI
  on `main`.
- The `.claude/settings.json` deny-list (force-push, `.env`/`CLAUDE.md`/`db/`
  writes, `manage.py flush`) still applies — never override it.
- Treat anything that pushes, deploys, or edits CI as "forbidden without explicit
  user confirmation," exactly as you would your own actions.

## Install (do this *with* the user)

Plugin installation is a user action in Claude Code — the agent can't silently
install a plugin — so walk the user through it:

1. Explain what it is and that it's optional.
2. Have them run `/plugin` in Claude Code.
3. Add the gstack marketplace, then install the gstack plugin. **If you don't
   already know the gstack marketplace location, ask the user** — they installed
   gstack themselves and can paste the `/plugin marketplace add …` source.
4. Once installed, the gstack skills (e.g. `/browse`, `/qa`) are available. Smoke
   test with `/browse` against the running app.

If the user would rather not, that's fine — record it and move on; they can ask
any time later.

## First load (offer once)

On the first session — while running `first-time-setup`, after the onboarding
and setup-decisions interviews — ask once (conversationally or via
`AskUserQuestion`):

> "There's an optional set of 'power tools' (gstack) that add browser testing,
> visual design review, and automatic bug-finding — handy but not required. Want
> me to help you set them up now, or skip for now?"

Record the choice in `setup_decisions.md` (`Power tools: installed / declined`)
so future sessions don't re-ask.
