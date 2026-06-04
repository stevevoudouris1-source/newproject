"""Test settings — used by pytest (see pyproject.toml).

Inherits dev (SQLite, DEBUG on) and tightens two things:
  - nplusone RAISES, so any N+1 query fails the test suite.
  - rate limiting is disabled by default to keep tests isolated; the dedicated
    rate-limit test re-enables it with @override_settings.
"""

from .dev import *  # noqa: F403

# An N+1 query is a test failure, not a warning.
NPLUSONE_RAISE = True

# Keep rate limiting out of the way of unrelated tests (shared LocMem cache would
# otherwise couple them). The rate-limit test turns it back on explicitly.
RATELIMIT_ENABLE = False
