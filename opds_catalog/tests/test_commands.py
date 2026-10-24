# -*- coding: utf-8 -*-
import os
from io import StringIO
from unittest import mock

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from constance import config
from opds_catalog.models import Book, Genre


class sopdsUtilTestCase(TestCase):
    fixtures = ['testdb.json']

    def setUp(self):
        self.test_root = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'tests', 'data')
        config.SOPDS_ROOT_LIB = self.test_root

    def test_info(self):
        out = StringIO()
        call_command('sopds_util', 'info', stdout=out)
        out.seek(0)
        text = out.getvalue()
        self.assertIn('Books count', text)
        self.assertIn('Authors count', text)

    def test_clear_reloads_genres(self):
        out = StringIO()
        call_command('sopds_util', 'clear', '--nogenres', stdout=out)
        self.assertEqual(Book.objects.count(), 0)
        self.assertEqual(Genre.objects.count(), 0)

        out = StringIO()
        call_command('sopds_util', 'clear', stdout=out)
        self.assertGreater(Genre.objects.count(), 0)
        self.assertEqual(Book.objects.count(), 0)

    def test_getconf_list(self):
        import contextlib
        out = StringIO()
        with contextlib.redirect_stdout(out):
            call_command('sopds_util', 'getconf')
        self.assertIn('SOPDS_ROOT_LIB', out.getvalue())


class sopdsScannerCommandTestCase(TestCase):

    def _command(self):
        import logging

        from opds_catalog.management.commands.sopds_scanner import Command
        cmd = Command()
        cmd.logger = logging.getLogger('')
        return cmd

    def test_stop_with_missing_pidfile(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            cmd = self._command()
            cmd.pidfile = os.path.join(tmp, 'missing.pid')
            out = StringIO()
            cmd.stdout = out
            cmd.handle(command='stop', daemonize=False, verbose=False)
            self.assertIn('Error stopping', out.getvalue())

    def test_stop_with_dead_pid(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            cmd = self._command()
            cmd.pidfile = os.path.join(tmp, 'scanner.pid')
            with open(cmd.pidfile, 'w') as f:
                f.write('999999999')
            out = StringIO()
            cmd.stdout = out
            cmd.handle(command='stop', daemonize=False, verbose=False)
            self.assertIn('Error stopping', out.getvalue())

    def test_check_settings_reschedules_on_change(self):
        cmd = self._command()
        cmd.sched = mock.MagicMock()
        cmd.SCAN_SHED_MIN = '0'
        cmd.SCAN_SHED_HOUR = '0,12'
        cmd.SCAN_SHED_DAY = '*'
        cmd.SCAN_SHED_DOW = '*'

        config.SOPDS_SCAN_SHED_HOUR = '*/2'
        cmd.check_settings()
        cmd.sched.reschedule_job.assert_called_once()

        cmd.sched.reset_mock()
        cmd.check_settings()
        cmd.sched.reschedule_job.assert_not_called()


class sopdsServerCommandTestCase(TestCase):

    def test_unsupported_action(self):
        from opds_catalog.management.commands.sopds_server import Command
        with self.assertRaises(CommandError):
            Command().handle(command='stop')

    def test_start_requires_gunicorn(self):
        from opds_catalog.management.commands import sopds_server
        with mock.patch.object(os.path, 'exists', return_value=False):
            with self.assertRaises(Exception) as ctx:
                sopds_server.Command().handle(command='start', host='127.0.0.1', port='8001', workers=1)
        self.assertIn('gunicorn', str(ctx.exception))


class scannerHandleScanTestCase(TestCase):

    def _command(self):
        import logging

        from opds_catalog.management.commands.sopds_scanner import Command
        cmd = Command()
        cmd.logger = logging.getLogger('')
        return cmd

    def test_handle_scan_runs_full_scan(self):
        import os

        test_root = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'tests', 'data')
        config.SOPDS_ROOT_LIB = test_root
        out = StringIO()
        call_command('sopds_scanner', 'scan', stdout=out)
        from opds_catalog.models import Book
        self.assertEqual(Book.objects.count(), 4)

    def test_update_shedule(self):
        cmd = self._command()
        cmd.sched = mock.MagicMock()
        config.SOPDS_SCAN_SHED_MIN = '*/30'
        cmd.update_shedule()
        cmd.sched.reschedule_job.assert_called_once()
        self.assertEqual(cmd.SCAN_SHED_MIN, '*/30')
        config.SOPDS_SCAN_SHED_MIN = '0'
