# Local development setup

This gets your forked app running on your own machine. Pick the section for your operating system, then do the **Both platforms** section at the end. You don't need to understand the commands — run each block, wait for it to finish, then hand off to Claude Code.

**You need:** Claude Code, Git, Python 3.13, [uv](https://docs.astral.sh/uv/) (the package manager), and a modern browser (Chrome recommended).

**You do NOT need:** Node, npm, Docker, or a local database. The app runs on a built-in SQLite file in "prototype" mode with zero setup.

**Only if you'll connect to a real SQL Server database:** the Microsoft ODBC Driver 18 (see the optional section near the end). Skip it for now if you're just prototyping.

---

## Mac (Apple Silicon or Intel)

Open **Terminal** (Cmd+Space, type "Terminal") and run these blocks one at a time, waiting for each to finish.

```bash
# 1. Install Homebrew (skip if `brew --version` already works)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 2. Install Git and Python 3.13
brew install git python@3.13

# 3. Install uv (the package manager — handles all Python dependencies)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 4. Reload your shell so `uv` is on your PATH
source ~/.zshrc   # or: exec $SHELL

# 5. Verify
git --version
python3.13 --version   # Python 3.13.x
uv --version
```

Install **Claude Code** if you haven't already: follow the instructions at https://docs.claude.com/claude-code. Make sure a modern browser (Chrome) is installed for in-app browser testing.

---

## Windows (native — no WSL required)

You'll install Claude Code, Git, Python 3.13, and uv. Everything runs natively.

1. **Install Claude Code** by following https://docs.claude.com/claude-code.

2. **Install Git for Windows** from https://git-scm.com/download/win.
   - Default options are fine. The installer includes **Git Bash**.
   - On the line-ending screen pick **"Checkout as-is, commit Unix-style line endings."**

3. **Install Python 3.13** from https://www.python.org/downloads/.
   - Download the **Windows installer (64-bit)** for **3.13.x**.
   - On the first screen, **check "Add python.exe to PATH"** before clicking Install. This is the step people forget.
   - Click "Install Now."

4. **Install uv** (the package manager). Open **PowerShell** and run:
   ```powershell
   powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
   ```
   Then **close and reopen** PowerShell so `uv` is on your PATH.

5. **Verify** in PowerShell:
   ```powershell
   git --version
   python --version    # Python 3.13.x
   uv --version
   ```

Make sure a modern browser (Chrome) is installed — the app uses it for browser testing.

Recommended: install **Windows Terminal** from the Microsoft Store for a nicer terminal.

---

## Both platforms — get the code and boot

1. **Create your repo from the template.** On the template's GitHub page, click the green **"Use this template"** button → **"Create a new repository."** Name it, then open *your* new repo's page.

2. **Clone it.** Click the green **"Code"** button on your repo page to copy the URL, then:
   ```bash
   git clone https://github.com/<owner>/<your-app>.git
   cd <your-app>
   ```

3. **Run setup.** This one script installs dependencies, creates your local config, sets up the database, and builds the styling:
   ```bash
   bin/setup
   ```

   If `bin/setup` isn't available on your system, run the underlying steps by hand:
   ```bash
   uv sync                                          # install all dependencies
   cp .env.example .env                             # create your local config (Windows PowerShell: copy .env.example .env)
   uv run python manage.py migrate                  # set up the database
   uv run python manage.py tailwind build           # build the CSS (downloads the Tailwind binary, no Node)
   uv run lefthook install                          # install the pre-commit hooks
   ```

4. **Start the server:**
   ```bash
   uv run python manage.py runserver
   ```

5. **Open** http://localhost:8000/ in your browser.

### Signing in the first time

Out of the box, standalone username/password sign-in is on (`PASSWORD_LOGIN_ENABLED`), and the built-in **Claude service account** (`claude@turn5.local`) can always sign in. Single sign-on (Microsoft Entra) is off until you configure it later — the app boots fine without it.

Hand the project to Claude Code from here. Claude can set the service account's password (env var `CLAUDE_ADMIN_PASSWORD` in your `.env`) and walk you through the first-run onboarding interview. To sign in manually, go to http://localhost:8000/accounts/login/.

To confirm the server is healthy at any time, visit http://localhost:8000/up/ — it should show `OK`.

---

## Optional: connecting to a real SQL Server database

You only need this if you're switching the app from prototype mode (the default SQLite file) to a real Microsoft SQL Server database. For prototyping, **skip this entirely.**

**Install the Microsoft ODBC Driver 18:**

- **Windows:** download and run the installer from https://learn.microsoft.com/sql/connect/odbc/download-odbc-driver-for-sql-server.
- **Mac:**
  ```bash
  brew tap microsoft/mssql-release
  brew install msodbcsql18
  ```

Then, in your `.env`, set `MODE=real` and add your connection string as `DATABASE_URL`. The shape is:

```
mssql://USER:PASSWORD@SERVER:1433/DBNAME?driver=ODBC+Driver+18+for+SQL+Server&Encrypt=yes&TrustServerCertificate=no
```

Ask Claude Code for help with the exact values — never paste real passwords into any file that gets committed to git. Your `.env` is gitignored and stays on your machine.

---

## Troubleshooting

**`uv: command not found` (or `uv` isn't recognized in PowerShell)**
The installer added `uv` to your PATH, but your current terminal was opened before that happened. **Close and reopen** your terminal. On Mac, you can instead run `source ~/.zshrc`. If it still fails, re-run the uv install command from your OS section above.

**`bin/setup` won't run / "permission denied"**
On Mac, run `chmod +x bin/setup` once, then `bin/setup` again. On Windows, run the underlying commands listed in step 3 by hand instead.

**Python version mismatch ("requires Python 3.13" or a different version runs)**
The project is pinned to Python 3.13 via `.python-version`. `uv` will pick the right interpreter automatically — try `uv sync` again. If you have multiple Pythons installed, confirm 3.13 is present with `python3.13 --version` (Mac) or `py -3.13 --version` (Windows). uv can also fetch it for you: `uv python install 3.13`.

**ODBC driver errors** (e.g. "Can't open lib 'ODBC Driver 18 for SQL Server'" or "data source name not found")
This only affects `MODE=real`. It means the Microsoft ODBC Driver 18 isn't installed or isn't found. Install it (see the optional section above), then reopen your terminal. Also double-check your `DATABASE_URL` driver name matches exactly: `ODBC+Driver+18+for+SQL+Server`. If you're just prototyping, set `MODE=prototype` (or remove `MODE`) in `.env` to fall back to SQLite.

**Tailwind build hangs or fails to download the binary**
`uv run python manage.py tailwind build` downloads a standalone Tailwind binary on first run (no Node involved). On a slow or restricted network this can stall. Re-run the command; if your network blocks the download, ask Claude Code or your IT contact about a proxy. The CSS is a build artifact (`static/css/tailwind.css`) and isn't committed — you can always rebuild it.

**Still stuck?**
Paste the exact error into your Claude Code session. Claude has the full project context and can diagnose setup issues directly.
