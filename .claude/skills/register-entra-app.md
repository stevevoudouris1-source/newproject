# Skill: Register a Microsoft Entra (Azure AD) App for SSO

Use this when you want your Turn 5 staff to sign in with their Microsoft work
accounts (Entra ID / Azure AD single sign-on). Until you do this, people sign in
with standalone username/password (on by default) or the Claude service account
— the app boots fine without SSO, so there's no rush. Do it when you want staff
to use their Microsoft accounts.

This is a one-time setup in the Azure Portal. It produces three values you paste
into `.env`. No code changes are needed — `mozilla-django-oidc` is already wired
up and serves `/oidc/authenticate/` (start login) and `/oidc/callback/` (return
from Microsoft).

> You need an Entra **admin** to do the portal steps (creating the registration
> and granting admin consent). If you're not an admin, send your IT contact this
> file — steps 1-5 are exactly what they need.

---

## Steps (in the Azure Portal)

### 1. New registration
- Go to **portal.azure.com** → **Microsoft Entra ID** → **App registrations** →
  **New registration**.
- **Name**: anything recognizable, e.g. `Turn 5 Internal App`.
- **Supported account types**: *Accounts in this organizational directory only*
  (single tenant) is the right default for an internal Turn 5 app.

### 2. Redirect URI (Web)
- Under **Redirect URI**, choose platform **Web**.
- For local development, enter exactly:

  ```
  http://localhost:8000/oidc/callback/
  ```

- Click **Register**.
- **Add the production URL later**, once you know it (e.g.
  `https://yourapp.turn5.local/oidc/callback/`). Do this back on the app's
  **Authentication** page → **Add a redirect URI**. The path is always
  `/oidc/callback/`; only the host changes.

### 3. Create a client secret
- Open the new app → **Certificates & secrets** → **Client secrets** →
  **New client secret**.
- Add a description and an expiry (e.g. 12 or 24 months — note the date so you
  rotate it before it lapses; expired secrets break login).
- **Copy the secret VALUE immediately.** Azure shows it once and never again. If
  you lose it, you just make a new one.
- Paste it somewhere safe for a moment — it goes into `.env` in step 6.

### 4. API permissions
- Open **API permissions** → **Add a permission** → **Microsoft Graph** →
  **Delegated permissions**.
- Add **`User.Read`** (the minimum — lets the app read the signed-in user's
  basic profile so we can match/create their account).
- Click **Grant admin consent for <your tenant>** and confirm. The status
  column should turn to a green check.

### 5. Collect the three values
From the app's **Overview** page, copy:
- **Directory (tenant) ID** → goes in `OIDC_TENANT_ID`
- **Application (client) ID** → goes in `OIDC_RP_CLIENT_ID`
- The **client secret value** from step 3 → goes in `OIDC_RP_CLIENT_SECRET`

---

## 6. Paste into `.env`

Open the project's `.env` (create it from `.env.example` if it doesn't exist —
`.env` is gitignored and is the **only** place secrets live). Add:

```dotenv
OIDC_TENANT_ID=00000000-0000-0000-0000-000000000000
OIDC_RP_CLIENT_ID=00000000-0000-0000-0000-000000000000
OIDC_RP_CLIENT_SECRET=your-client-secret-value-here
```

Replace the placeholders with your real values. **Never commit `.env`** and
never paste the secret into any tracked file, chat, or `.env.example`
(`.env.example` holds key names only, never values).

The login endpoints derive from the tenant ID automatically
(`login.microsoftonline.com` for auth, `graph.microsoft.com/oidc/userinfo` for
the profile) — you do **not** need to set any URLs.

---

## 7. Verify it works
- Restart the dev server so the new env vars load:

  ```
  uv run python manage.py runserver
  ```

- Go to **http://localhost:8000/** — you should be redirected to log in. The
  Microsoft sign-in option appears only once these three vars are set (the
  `EntraOIDCBackend` registers itself only when OIDC is configured).
- Sign in with a Microsoft work account. You should land back on the app at
  `Hello, <your-email>!`.

### If something goes wrong
- **Redirect URI mismatch error** → the URI in Azure must match exactly,
  including the trailing slash: `http://localhost:8000/oidc/callback/`.
- **Invalid client secret** → you may have copied the secret **ID** instead of
  the **value**, or it expired. Make a new one (step 3) and update `.env`.
- **Consent / permission error** → an admin still needs to **Grant admin
  consent** for `User.Read` (step 4).
- **No Microsoft button on the login page** → one of the three `OIDC_*` vars is
  missing or misspelled; the SSO backend only turns on when all three are set.
  You can still sign in meanwhile with username/password at `/accounts/login/`
  (the Claude service account, or any user with a password).

---

## Notes
- The app is **fine without this**. Skip it entirely if you only need the Claude
  service account for now; come back when staff need to log in.
- Adding production later = just add the prod redirect URI in Azure (step 2) and
  set the same three vars in your production `.env`/environment.
- Rotating the secret on expiry = repeat step 3 (new secret value) and update
  `OIDC_RP_CLIENT_SECRET` in `.env`. Old logins keep working until the old
  secret actually expires.
