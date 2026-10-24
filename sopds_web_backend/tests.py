# -*- coding: utf-8 -*-

from urllib.parse import quote

from django.urls import reverse
from django.test import TestCase, Client
from django.contrib.auth.models import User

from constance import config


class LoginRedirectTestCase(TestCase):

    def setUp(self):
        config.SOPDS_AUTH = True
        self.user = User.objects.create_user('tester', password='secret123')
        self.login_url = reverse('web:login')

    def _login(self, next_url):
        return Client().post(
            '%s?next=%s' % (self.login_url, quote(next_url, safe='')),
            {'username': 'tester', 'password': 'secret123'},
        )

    def test_absolute_external_next_is_rejected(self):
        response = self._login('https://evil.example/phish')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], '/web/')

    def test_protocol_relative_next_is_rejected(self):
        response = self._login('//evil.example')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], '/web/')

    def test_relative_next_is_kept(self):
        response = self._login('/web/search/books/?searchtype=m&searchterms=x')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], '/web/search/books/?searchtype=m&searchterms=x')

    def test_no_next_redirects_to_main(self):
        response = Client().post(
            self.login_url,
            {'username': 'tester', 'password': 'secret123'},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], '/web/')

    def test_wrong_password_stays_on_login_page(self):
        response = Client().post(
            '%s?next=https://evil.example' % self.login_url,
            {'username': 'tester', 'password': 'wrong'},
        )
        self.assertEqual(response.status_code, 403)
