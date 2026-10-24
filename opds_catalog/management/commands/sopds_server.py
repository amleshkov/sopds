import os
import sys

from django.conf import settings as main_settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'HTTP/OPDS production server (gunicorn)'

    def add_arguments(self, parser):
        parser.add_argument('command', help='Use [ start ]')
        parser.add_argument('--host', action='store', dest='host', default='0.0.0.0', help='Set server binding address')
        parser.add_argument('--port', action='store', dest='port', default=8001, help='Set server port')
        parser.add_argument('--workers', action='store', dest='workers', type=int,
                            default=int(os.environ.get('SOPDS_WEB_WORKERS', 2)), help='Number of gunicorn workers')

    def handle(self, *args, **options):
        action = options['command']
        if action != 'start':
            raise CommandError('Action "%s" is not supported. The server runs in the foreground; '
                               'stop or restart it through the process manager (systemctl restart sopds).' % action)

        gunicorn = os.path.join(os.path.dirname(sys.executable), 'gunicorn')
        if not os.path.exists(gunicorn):
            raise CommandError('gunicorn is not installed in %s' % os.path.dirname(sys.executable))

        os.execv(gunicorn, [
            gunicorn,
            '--chdir', main_settings.BASE_DIR,
            '--bind', '%s:%s' % (options['host'], options['port']),
            '--workers', str(options['workers']),
            '--access-logfile', '-',
            'sopds.wsgi:application',
        ])
