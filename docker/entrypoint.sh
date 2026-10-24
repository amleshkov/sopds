#!/bin/sh
set -e

ROLE="${1:-server}"
if [ "$#" -gt 0 ]; then shift; fi

wait_for_db() {
    python - <<'PYEOF'
import os
import sys
import time

import psycopg2

for _ in range(60):
    try:
        psycopg2.connect(
            dbname=os.environ.get('SOPDS_DB_NAME', 'sopds'),
            user=os.environ.get('SOPDS_DB_USER', 'sopds'),
            password=os.environ.get('SOPDS_DB_PASSWORD', 'sopds'),
            host=os.environ.get('SOPDS_DB_HOST'),
            port=os.environ.get('SOPDS_DB_PORT', '5432'),
        ).close()
        sys.exit(0)
    except Exception:
        time.sleep(2)
sys.exit(1)
PYEOF
}

wait_for_server() {
    python - <<'PYEOF'
import os
import sys
import time
import urllib.request

host = os.environ.get('SOPDS_SERVER_HOST', 'sopds-server')
port = os.environ.get('SOPDS_PORT', '8001')
url = 'http://%s:%s/opds/' % (host, port)

for _ in range(90):
    try:
        urllib.request.urlopen(url, timeout=3)
        sys.exit(0)
    except Exception as e:
        if getattr(e, 'code', None):
            sys.exit(0)
        time.sleep(2)
sys.exit(1)
PYEOF
}

wait_for_db

if [ "$ROLE" = "server" ]; then
    python manage.py migrate --noinput

    GENRES=$(python manage.py shell -c "from opds_catalog.models import Genre; print(Genre.objects.count())")
    if [ "$GENRES" = "0" ]; then
        python manage.py loaddata genre.json
    fi

    python manage.py sopds_util setconf SOPDS_ROOT_LIB /data
    python manage.py sopds_util setconf SOPDS_AUTH False

    exec python manage.py sopds_server start --host 0.0.0.0 --port "${SOPDS_PORT:-8001}"
fi

if [ "$ROLE" = "scanner" ]; then
    wait_for_server
    exec python manage.py sopds_scanner "$@"
fi

exec "$@"
