# -*- coding: utf-8 -*-

from django.urls import reverse
from django.test import TestCase, Client

from constance import config

PAYLOADS = ["'", '"', "';--", "\\", "' union select 1,2,3 --"]


class charFeedsInjectionTestCase(TestCase):
    fixtures = ['testdb.json']

    def setUp(self):
        config.SOPDS_AUTH = False

    def test_char_feeds_injection_payloads(self):
        c = Client()
        for payload in PAYLOADS:
            for url_name in ['chars_books', 'chars_authors', 'chars_series']:
                response = c.get(reverse('opds:' + url_name, kwargs={'lang_code': 0, 'chars': payload}))
                self.assertEqual(response.status_code, 200, '%s with payload %r' % (url_name, payload))
                response = c.get(reverse('opds:' + url_name, kwargs={'lang_code': 1, 'chars': payload}))
                self.assertEqual(response.status_code, 200, '%s with payload %r' % (url_name, payload))

    def test_web_alphabet_views_injection_payloads(self):
        c = Client()
        for payload in PAYLOADS:
            for url_name in ['book', 'author', 'series']:
                response = c.get(reverse('web:' + url_name), {'lang': 0, 'chars': payload})
                self.assertEqual(response.status_code, 200, '%s with payload %r' % (url_name, payload))
                response = c.get(reverse('web:' + url_name), {'lang': 1, 'chars': payload})
                self.assertEqual(response.status_code, 200, '%s with payload %r' % (url_name, payload))

    def test_char_feed_drilldown_still_works(self):
        c = Client()
        response = c.get(reverse('opds:chars_books', kwargs={'lang_code': 0, 'chars': 'Д'}))
        self.assertEqual(response.status_code, 200)
        self.assertIn('<title>ДР', response.content.decode())

    def test_web_alphabet_drilldown_still_works(self):
        c = Client()
        response = c.get(reverse('web:book'), {'lang': 0, 'chars': 'Д'})
        self.assertEqual(response.status_code, 200)
        self.assertIn('ДР', response.content.decode())
