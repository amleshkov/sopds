#### SimpleOPDS Catalog
#### Author: Dmitry V.Shelepnev
#### Modernized fork: Python 3.12, Django 5.2 LTS

OPDS catalog server for home book collections: scans a library directory
(loose files and zip archives, INPX collections supported), serves the catalog
through OPDS feeds and a web UI, runs scheduled rescans.

- Stack: Python 3.12, Django 5.2 LTS, PostgreSQL (or sqlite3), gunicorn, WhiteNoise
- Quality: 117 unit tests, docker-based e2e in CI (scan, API, web, byte-exact downloads), ruff-clean, coverage gate
- Removed relative to the original 0.47: Telegram bot, fb2 to epub/mobi converters, vendored django-constance, vendored zipfile fork

[Инструкция на русском языке: README_RUS.md](README_RUS.md)

#### 1. Quick start (bare metal)

1.1 Get the code and build the environment:

    git clone <this repository> sopds
    cd sopds
    python3.12 -m venv djenv
    djenv/bin/pip install -r requirements.txt

1.2 Set environment variables (see section 2 for the full list). The minimum:

    export SOPDS_SECRET_KEY="$(openssl rand -base64 50)"
    export SOPDS_ALLOWED_HOSTS="localhost,your-host"
    export SOPDS_DEBUG=True

With `SOPDS_DEBUG=True` the development static-file serving is enabled;
for production use gunicorn + WhiteNoise (systemd/docker below handle it).

1.3 Initialize the database (sqlite3 by default; PostgreSQL via `SOPDS_DB_HOST`):

    djenv/bin/python manage.py migrate
    djenv/bin/python manage.py loaddata genre.json
    djenv/bin/python manage.py createsuperuser

1.4 Point the catalog at your library and rescan:

    djenv/bin/python manage.py sopds_util setconf SOPDS_ROOT_LIB /path/to/books
    djenv/bin/python manage.py sopds_scanner scan

1.5 Start the server (gunicorn, foreground):

    djenv/bin/python manage.py sopds_server start --host 0.0.0.0 --port 8001

Access:

>     OPDS feed: http://localhost:8001/opds/
>     Web UI:    http://localhost:8001/web/
>     Admin:     http://localhost:8001/admin/

Enable authentication (`SOPDS_AUTH` constance setting) to require login
(web) and HTTP Basic auth (OPDS) for the catalog.

#### 2. Environment variables

    SOPDS_SECRET_KEY      required, Django secret key
    SOPDS_DEBUG           True/False, default False
    SOPDS_ALLOWED_HOSTS   comma-separated list of allowed hosts
    SOPDS_DB_HOST         PostgreSQL host; when set, PostgreSQL is used instead of sqlite3
    SOPDS_DB_NAME         PostgreSQL database name (default: sopds)
    SOPDS_DB_USER         PostgreSQL user (default: sopds)
    SOPDS_DB_PASSWORD     PostgreSQL password (default: sopds)
    SOPDS_DB_PORT         PostgreSQL port (default: 5432)
    SOPDS_STATIC_ROOT     collectstatic output directory (default: <project>/staticroot)
    SOPDS_WEB_WORKERS     gunicorn worker count (default: 2)

All other settings live in the database (django-constance) and are edited
through the admin UI (`/admin/`) or `manage.py sopds_util setconf` — see section 5.

#### 3. Docker

    python scripts/make_testbooks.py testdata     # optional demo library
    docker compose up -d --build

Services: `postgres` (16), `sopds-server` (gunicorn, port 8001),
`sopds-scanner` (scheduled rescans). The library directory is mounted at `/data`
(set `SOPDS_LIB_DIR` to point at your collection).

Run a one-off scan:

    docker compose run --rm sopds-scanner scanner scan

#### 4. systemd deployment

`sopds_server start` runs gunicorn in the foreground — process management
belongs to systemd (or docker). Ready unit files for the reference layout
(project in `/opt/sopds/sopds`, venv in `/opt/sopds/djenv`, env vars in
`/opt/sopds/sopds-env.sh`) are in `deploy/`:

    cp deploy/*.service /etc/systemd/system/
    systemctl daemon-reload
    systemctl enable --now sopds.service sopds-scanner.service

Units run `migrate` and `collectstatic` before start and restart on failure.

#### 5. Catalog settings (django-constance)

Settings marked (constance) are stored in the database, editable via
`/admin/` or:

    python manage.py sopds_util setconf KEY VALUE
    python manage.py sopds_util getconf [KEY]

Key settings:

**SOPDS_ROOT_LIB** - absolute path to the books collection directory.
**SOPDS_AUTH** - require authentication for OPDS/web (default True).
**SOPDS_LANGUAGE** - interface language, ru-RU or en-US.
**SOPDS_BOOK_EXTENSIONS** - managed book file extensions (default ".pdf .djvu .fb2 .epub .mobi").
**SOPDS_MAXITEMS** - items per page (default 60).
**SOPDS_DOUBLES_HIDE** - hide duplicate books in listings (default True).
**SOPDS_ZIPSCAN** - scan books inside zip archives (default True).
**SOPDS_ZIPCODEPAGE** - codepage for filenames inside zip archives (default cp866).
**SOPDS_INPX_ENABLE** - read metadata from .inpx collections (default False).
**SOPDS_DELETE_LOGICAL** - mark missing books unavailable instead of deleting rows (default False).
**SOPDS_SCAN_SHED_MIN/HOUR/DAY/DOW** - scanner cron schedule (constance).
**SOPDS_SCAN_START_DIRECTLY** - set True to trigger an extra scan on the next scheduler check.
**SOPDS_CACHE_TIME** - cover cache time in seconds (default 1200).
**SOPDS_TITLE_AS_FILENAME** - build download filenames from book titles (default True).

#### 6. Console commands

    python manage.py sopds_scanner scan              # one full scan
    python manage.py sopds_scanner start             # scheduled scans (cron from settings)
    python manage.py sopds_util info                 # collection statistics
    python manage.py sopds_util clear [--nogenres]   # wipe catalog (reloads genres by default)
    python manage.py sopds_util save_mygenres        # dump current genres to fixtures
    python manage.py sopds_util load_mygenres        # load genres from fixtures
    python manage.py sopds_util pg_optimize          # PostgreSQL table optimization

#### 7. Upgrading from the original SimpleOPDS 0.47-devel

The upgrade moves the project to Python 3.12 and Django 5.2 LTS. The database (books, authors,
settings changed through the admin UI) is preserved.

7.1 Stop the running services:

    python3 manage.py sopds_server stop
    python3 manage.py sopds_scanner stop

If you used the Telegram bot (`sopds_telebot`), stop and remove its service as well — the bot
and the fb2 to epub/mobi converters are no longer part of the project.

7.2 Back up the database (mandatory):

    pg_dump -U sopds sopds > sopds_backup.sql        # PostgreSQL
    cp db.sqlite3 db.sqlite3.bak                     # sqlite3

7.3 Update the project code (git pull or replace the directory).

7.4 Build a new Python 3.12 environment and install the pinned dependencies
(the old Python 3.9 environment is not compatible):

    python3.12 -m venv djenv
    djenv/bin/pip install -r requirements.txt

7.5 Configure the application through environment variables (previously database credentials
were edited directly in sopds/settings.py):

    SOPDS_SECRET_KEY=<generate with: openssl rand -base64 50>   # required
    SOPDS_DB_HOST=<host> SOPDS_DB_NAME=sopds SOPDS_DB_USER=sopds SOPDS_DB_PASSWORD=...   # PostgreSQL only
    SOPDS_ALLOWED_HOSTS=<comma-separated host list>
    SOPDS_DEBUG=True|False

For systemd deployments add these variables to the EnvironmentFile (for example /opt/sopds/sopds-env.sh).

7.6 Prepare and run the migrations. The old vendored constance settings table needs a one-time
helper run before Django migrations convert it (works for PostgreSQL and sqlite3):

    djenv/bin/python scripts/migrate_constance_legacy.py
    djenv/bin/python manage.py migrate

All settings changed through the admin interface are carried over automatically.

7.7 Start the services and verify:

    djenv/bin/python manage.py sopds_server start
    djenv/bin/python manage.py sopds_scanner start

    curl http://localhost:8001/opds/

#### 8. Development

    pip install -r requirements.txt -r requirements-dev.txt
    python manage.py test                          # unit tests
    coverage run manage.py test && coverage report # coverage (gate: 72%)
    ruff check .                                   # linter
    docker compose up -d --build && docker compose run --rm sopds-scanner scanner scan   # e2e locally

CI (GitHub Actions): lint (ruff), unit tests with coverage gate,
docker e2e (generated demo library, scan, OPDS/web checks, byte-exact downloads).
