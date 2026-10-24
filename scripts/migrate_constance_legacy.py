import os
import sys

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sopds.settings')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()

from django.db import connection


def main():
    if connection.vendor not in ('postgresql', 'sqlite'):
        print('this helper only supports postgresql and sqlite, current vendor: %s' % connection.vendor)
        return

    with connection.cursor() as cursor:
        tables = connection.introspection.table_names(cursor)
        if 'constance_config' not in tables:
            print('legacy constance_config table not found, nothing to do')
            return

        columns = [column.name for column in connection.introspection.get_table_description(cursor, 'constance_config')]
        if 'id' in columns:
            print('legacy constance_config already has id column, nothing to do')
            return

        cursor.execute('alter table constance_config add column id integer')
        cursor.execute(
            'update constance_config set id = sub.rn '
            'from (select key, row_number() over () as rn from constance_config) as sub '
            'where constance_config.key = sub.key'
        )
    print('added id column to legacy constance_config, ready for manage.py migrate')


if __name__ == '__main__':
    main()
