# Vendored front-end libraries

These are committed (not fetched from a CDN) so the app works offline and has no
runtime dependency on third-party hosts. Loaded from `templates/base.html`.

| File            | Library | Version | Source |
|-----------------|---------|---------|--------|
| `htmx.min.js`   | htmx    | 2.0.4   | https://unpkg.com/htmx.org@2.0.4/dist/htmx.min.js |
| `alpine.min.js` | Alpine.js | 3.14.8 | https://cdn.jsdelivr.net/npm/alpinejs@3.14.8/dist/cdn.min.js |

## Upgrading

Download the new pinned version over the existing file, update the version in
this table, and re-run the test suite + a quick manual smoke test:

```bash
# example: bump htmx
curl -L https://unpkg.com/htmx.org@<version>/dist/htmx.min.js -o static/vendor/htmx.min.js
```

Do not add other CDN `<script>` tags to `base.html`; vendor new libraries here
instead so the no-Node, offline-friendly guarantee holds.
