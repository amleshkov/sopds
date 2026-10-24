import os
import sys

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sopds.settings')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()

from django.db import connection


def main():
    if connection.vendor != 'postgresql':
        print('this helper is only needed for the legacy postgresql stand database')
        return

    with connection.cursor() as cursor:
        cursor.execute(
            "select column_name from information_schema.columns where table_name = 'constance_config'"
        )
        columns = [row[0] for row in cursor.fetchall()]

    if not columns:
        print('legacy constance_config table not found, nothing to do')
        return

    if 'id' in columns:
        print('legacy constance_config already has id column, nothing to do')
        return

    with connection.cursor() as cursor:
        cursor.execute('alter table constance_config add column id integer')
        cursor.execute(
            'update constance_config set id = sub.rn '
            'from (select key, row_number() over () as rn from constance_config) as sub '
            'where constance_config.key = sub.key'
        )
    print('added id column to legacy constance_config, ready for manage.py migrate')


if __name__ == '__main__':
    main()
