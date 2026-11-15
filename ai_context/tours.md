# Feature doc: 3D facility tour (`apps.tours`)

**Purpose.** Shows a Matterport 3D walkthrough of a Turn 5 facility inside the
app, at `/tour/` (URL name `tour`), linked from the nav bar as "3D Tour".

**Key files**
- `apps/tours/views.py` — the `tour` view and the `MATTERPORT_TOUR_URL` constant
  (the public Matterport share link; not a secret). Change the id after `m=` to
  show a different space.
- `apps/tours/urls.py`, `templates/tours/tour.html` (the `<iframe>` + an "Open in
  a new tab" fallback), `tests/test_tour.py`.

**Access.** `@login_required` only — every signed-in employee can view it. There
is no model and no per-user data, so no `authorize(...)` / `for_user(...)` call.
If tours ever need restricting, register a permission (see
`.claude/skills/add-permission.md`).

**Security.** The CSP has `frame-src: https://my.matterport.com` — the only
third-party host the app may embed. A guard test pins this to that single host.

**Gotchas**
- The tour itself is hosted by Matterport. If the space is set to private or
  password-protected in Matterport, the frame shows Matterport's own prompt.
- Cloud Claude sessions can't reach `my.matterport.com`, so the frame renders
  empty there; verify the 3D content from a normal browser.
- There is one tour and no database table. If the user wants several tours,
  build a `Tour` model + list page (see `.claude/skills/add-model.md`).
