# Hosting-agnostic production image. Hosting target is still TBD (Azure App
# Service vs Container Apps vs on-prem) — ask Matt before the first deploy.
#
# Builds static assets at image-build time using throwaway env values, then runs
# under config.settings.prod (which requires real SECRET_KEY / ALLOWED_HOSTS /
# DATABASE_URL supplied at runtime by the platform's secret store).

FROM python:3.13-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DJANGO_SETTINGS_MODULE=config.settings.prod

# uv (copied from the official image — no pip needed).
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# unixODBC is needed by pyodbc (SQL Server mode). The Microsoft ODBC Driver 18
# itself is added when SQL Server hosting is chosen (see ai_context/setup.md).
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential unixodbc unixodbc-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install deps first for layer caching.
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-dev

# App source.
COPY . .

# Build Tailwind + collect static with throwaway build-time env (no real secrets).
RUN SECRET_KEY=build-only-not-a-secret \
    ALLOWED_HOSTS=localhost \
    DATABASE_URL=sqlite:////tmp/build.sqlite3 \
    sh -c "uv run python manage.py tailwind build && uv run python manage.py collectstatic --noinput"

EXPOSE 8000

# Gunicorn WSGI server. Run migrations as a separate platform step/release command.
CMD ["uv", "run", "gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
