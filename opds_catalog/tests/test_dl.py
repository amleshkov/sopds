# -*- coding: utf-8 -*-

import os

from django.urls import reverse
from django.test import TestCase, Client
from django.contrib.auth.models import User

from constance import config


class DownloadsAuthTestCase(TestCase):
    fixtures = ['testdb.json']

    def setUp(self):
        self.test_root = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
        config.SOPDS_ROOT_LIB = self.test_root
        self.user = User.objects.create_user('tester', password='secret123')
        self.download_url = reverse('opds:download', kwargs={'book_id': 5, 'zip_flag': 0})
        self.cover_url = reverse('opds:cover', kwargs={'book_id': 5})
        self.thumb_url = reverse('opds:thumb', kwargs={'book_id': 5})

    def test_download_denied_anonymous_when_auth_on(self):
        config.SOPDS_AUTH = True
        response = Client().get(self.download_url)
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response['WWW-Authenticate'], 'Basic realm="OPDS"')

    def test_download_denied_wrong_password_when_auth_on(self):
        config.SOPDS_AUTH = True
        response = Client().get(self.download_url, HTTP_AUTHORIZATION='Basic dGVzdGVyOndyb25n')
        self.assertEqual(response.status_code, 401)

    def _basic(self):
        import base64
        return 'Basic ' + base64.b64encode(b'tester:secret123').decode()

    def test_download_ok_with_basic_auth(self):
        config.SOPDS_AUTH = True
        response = Client().get(self.download_url, HTTP_AUTHORIZATION=self._basic())
        self.assertEqual(response.status_code, 200)
        self.assertGreater(len(response.content), 0)

    def test_download_ok_with_session_auth(self):
        config.SOPDS_AUTH = True
        c = Client()
        c.force_login(self.user)
        response = c.get(self.download_url)
        self.assertEqual(response.status_code, 200)

    def test_cover_and_thumb_require_auth(self):
        config.SOPDS_AUTH = True
        response = Client().get(self.cover_url)
        self.assertEqual(response.status_code, 401)
        response = Client().get(self.thumb_url)
        self.assertEqual(response.status_code, 401)

    def test_download_allowed_anonymous_when_auth_off(self):
        config.SOPDS_AUTH = False
        response = Client().get(self.download_url)
        self.assertEqual(response.status_code, 200)
