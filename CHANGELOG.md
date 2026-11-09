# Changelog

All notable changes to this fork relative to the original SimpleOPDS 0.47-devel
(by Dmitry V. Shelepnev, www.sopds.ru) are documented here.
The format loosely follows [Keep a Changelog](https://keepachangelog.com/).

## [1.0.0] - 2026-11-09

The first stable release of the modernized fork. The original codebase
(Django 2.1 / Python 3.4-3.9 era, last upstream commit 2019-04-13) was
security-audited, migrated to a current stack, refactored and covered with
tests, CI and e2e infrastructure. Deployed and verified on a production stand
with a ~963k book collection.

### Security

- Fixed SQL injection in the alphabet drill-down pages and feeds: user-controlled
  `chars` was interpolated into raw SQL via `%`-formatting (6 places across
  `sopds_web_backend/views.py` and `opds_catalog/feeds.py`); all values are now
  passed as parameters (`raw(sql, params)`).
- Removed command injection in fb2 conversion: `subprocess.Popen(..., shell=True)`
  with paths built from book filenames. The entire converter feature was removed
  (see Removed).
- Fixed authentication bypass: with `SOPDS_AUTH=True` OPDS feeds required auth,
  but `/opds/download/`, `/opds/cover/` and `/opds/convert/` served the whole
  library to anyone. All download/cover views are now protected by the same
  Basic-auth mechanism (`sopds_auth_required` decorator).
- Fixed open redirect in the web login (`next` parameter validated with
  `url_has_allowed_host_and_scheme`).
- Bookshelf mutations (delete/clear) moved from GET links to POST forms with
  CSRF protection.
- Re-enabled HTML autoescaping in the OpenSearch template (was blanket
  `{% autoescape off %}`).
- Fixed cross-request state leakage in OPDS feeds: feed instances were shared
  across requests (`self.request`, `self.author_id`, `self.lang_code`,
  `self.section_id` written per request); each request now runs on its own
  feed instance.
- Hardened `BasicAuthMiddleware` against malformed `Authorization` headers
  (401 instead of a 500).
- Removed the hardcoded `SECRET_KEY` from the repository; the key is now
  mandatory via the `SOPDS_SECRET_KEY` environment variable (fail-fast).
  `DEBUG` defaults to `False`, `ALLOWED_HOSTS` comes from the environment.

### Stack / dependencies

- Python 3.9 -> 3.12, Django 2.1 -> 5.2 LTS.
- Project management moved to uv: `pyproject.toml` (dependencies + dev group +
  consolidated ruff/coverage configuration), `uv.lock`, `.python-version`.
- Vendored django-constance 2.4 replaced with the pip package (4.4); settings
  values survive the upgrade automatically (constance's own migrations copy the
  legacy table and convert pickled values to JSON; a helper
  `scripts/migrate_constance_legacy.py` prepares legacy databases).
- Vendored 1770-line zipfile fork (`zipf.py`) replaced with a 25-line shim over
  the stdlib `zipfile(metadata_encoding=...)` for cp866 archive names.
- The 206-line legacy `fb2parse.py` parser removed (the scanner instantiated it
  and never used it).
- APScheduler, Pillow, lxml, psycopg2-binary updated to current versions;
  `django-picklefield` dropped (only the vendored constance needed it).

### Removed

- Telegram bot support (`sopds_telebot` command, settings, dependencies).
- fb2 to epub/mobi converters (`ConvertFB2` view, `convert/` route and the
  bundled converter binaries; the epub writer/DRM code block and the aes.py
  stub were dead even before removal).
- Book format support itself was kept: fb2, epub, mobi, pdf and djvu all work
  as before (pdf/djvu via the no-metadata `Dummy` handler).

### Bug fixes

- Thumbnails returned HTTP 500 under Pillow >= 10 (`Image.ANTIALIAS` removed
  upstream; now `Image.LANCZOS`).
- INPX parsing corrupted book paths: `.inp` lines kept trailing `\n`, breaking
  the FOLDER field (feature is disabled by default, which is why nobody
  noticed for ~10 years).
- Unknown genre id crashed the genres feed with a 500 (now 404).
- Scanner froze forever after any crash: the `scan_is_active` flag was never
  reset (now reset in `finally`).
- Reading `stop`/`restart` actions crashed without a pidfile.
- Downloads/covers of missing books returned 500 instead of 404.
- Invalid integer query parameters (`?page=abc`, `?lang=abc`, ...) crashed
  pages with 500.
- The `searchtype=d`/`i` views crashed on invalid or unknown book ids.
- `SOPDS_DELETE_LOGICAL` now actually works: the branch was commented out and
  no query ever filtered by `avail`; `Book.objects` now excludes logically
  deleted books (`avail=0`) while the scanner operates on `all_objects`.
- Fixed broken `default=None` on NOT NULL `search_*` fields (real default `''`).

### Database

- Through models renamed: `bauthor`/`bgenre`/`bseries` -> `BookAuthor`/
  `BookGenre`/`BookSeries` (instant table renames).
- Unique constraints added: `Book(filename, path)` and `Catalog(path)` —
  duplicates are now impossible at the database level (previously papered over
  by the `SOPDS_DOUBLES_HIDE` display flag); migrations de-duplicate existing
  data before adding each constraint.
- Composite indexes `(path, avail)` and `(catalog, avail)` on Book.

### Performance

- Fixed N+1 queries throughout: per-author book counts (`annotate(Count)`),
  bookshelf lookups (filtered `Prefetch`), per-row M2M loads
  (`prefetch_related` on page slices, ~250 queries per 60-book page -> ~6).
- Book downloads stream via `FileResponse` instead of reading whole files
  into memory.
- Scanner commits in batches (100 loose files / per archive) instead of one
  giant transaction over the whole library; a failed batch is logged and the
  scan continues.
- Scanner hardened: `os.walk` error callback, symlink-loop guard, vanished
  files and broken/encrypted archives logged and skipped instead of killing
  the scan.

### Deployment

- Production server is gunicorn (the `sopds_server start` command exec's it in
  the foreground); the hand-rolled daemonize/pidfile/runserver path is gone.
- Static files served by WhiteNoise (`collectstatic` into a separate
  `staticroot/`; previously `STATIC_ROOT` pointed at the source tree).
- systemd unit templates in `deploy/` (Type=simple, ExecStartPre
  migrate+collectstatic, After=postgresql.service, Restart=on-failure).
- Docker: `Dockerfile` + `docker-compose.yml` (postgres 16, server, scanner)
  built via pinned uv; the docker environment runs production-like
  (`DEBUG=False`).
- Configuration moved from editing `settings.py` to environment variables
  (`SOPDS_SECRET_KEY`, `SOPDS_DB_*`, `SOPDS_ALLOWED_HOSTS`, `SOPDS_DEBUG`,
  `SOPDS_STATIC_ROOT`, `SOPDS_WEB_WORKERS`).

### Quality / infrastructure

- Test suite grown from 40 to 116 tests: security regressions (injection
  payloads, auth bypass, CSRF, redirects), downloads byte-identity, INPX
  end-to-end, scanner resilience, migration tests (de-duplication via
  `MigrationExecutor`), feed/page smoke tests, query-count guards.
- Coverage gate: 75% (fail-under 72) enforced in CI.
- ruff linting (clean, autofixed 166 violations incl. 19 bare `except:`),
  pinned in the dev dependency group.
- CI (GitHub Actions): lint job, unit tests with coverage, docker e2e job
  (generated demo library, double scan idempotency, OPDS/web checks,
  byte-exact downloads, injection payload checks).
- Travis CI config removed.
- README rewritten for the new stack (quick start, env vars, Docker, systemd,
  upgrade-from-0.47 guide, development section); Russian README kept in sync.

### Upgrade notes

See README section 7 (Upgrading from the original SimpleOPDS 0.47-devel).
Key points: back up the database, build the uv environment, run
`scripts/migrate_constance_legacy.py` + `manage.py migrate`, put the
environment variables into the systemd EnvironmentFile. PostgreSQL 14+ is
required (Django 5.2); the reference stand was upgraded 13 -> 16.
