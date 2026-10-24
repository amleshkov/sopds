# -*- coding: utf-8 -*-

from urllib.parse import quote

from django.urls import reverse
from django.test import TestCase, Client
from django.contrib.auth.models import User

from constance import config

from opds_catalog.models import Book, bookshelf


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


class BookshelfMutationTestCase(TestCase):
    fixtures = ['testdb.json']

    def setUp(self):
        config.SOPDS_AUTH = True
        self.user = User.objects.create_user('tester', password='secret123')
        bookshelf.objects.create(user=self.user, book=Book.objects.get(id=5))
        self.c = Client()
        self.c.force_login(self.user)

    def shelf_count(self):
        return bookshelf.objects.filter(user=self.user).count()

    def test_delete_via_get_rejected(self):
        response = self.c.get(reverse('web:bsdel'), {'book': 5})
        self.assertEqual(response.status_code, 405)
        self.assertEqual(self.shelf_count(), 1)

    def test_delete_via_post_works(self):
        response = self.c.post(reverse('web:bsdel'), {'book': 5})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.shelf_count(), 0)

    def test_delete_invalid_book_param(self):
        response = self.c.post(reverse('web:bsdel'), {'book': 'abc'})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.shelf_count(), 1)

    def test_delete_requires_csrf_token(self):
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.user)
        response = csrf_client.post(reverse('web:bsdel'), {'book': 5})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.shelf_count(), 1)

    def test_clear_via_get_rejected(self):
        response = self.c.get(reverse('web:bsclear'))
        self.assertEqual(response.status_code, 405)
        self.assertEqual(self.shelf_count(), 1)

    def test_clear_via_post_works(self):
        response = self.c.post(reverse('web:bsclear'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.shelf_count(), 0)


class queryCountTestCase(TestCase):
    fixtures = ['testdb.json']

    def setUp(self):
        config.SOPDS_AUTH = False
        from django.contrib.auth.models import User
        self.user = User.objects.create_user('counter', password='secret123')

    def test_authors_page_counts_without_n_plus_1(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        c = Client()
        with CaptureQueriesContext(connection) as ctx:
            response = c.get(reverse('web:searchauthors'), {'searchtype': 'm', 'searchterms': ''})
        self.assertEqual(response.status_code, 200)
        author_queries = [q['sql'] for q in ctx.captured_queries
                          if 'opds_catalog_author' in q['sql'] or 'opds_catalog_bookauthor' in q['sql']]
        self.assertLessEqual(len(author_queries), 3, author_queries)

    def test_books_page_lists_without_n_plus_1(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        c = Client()
        with CaptureQueriesContext(connection) as ctx:
            response = c.get(reverse('web:searchbooks'), {'searchtype': 'm', 'searchterms': ''})
        self.assertEqual(response.status_code, 200)
        link_queries = [q['sql'] for q in ctx.captured_queries
                        if any(table in q['sql'] for table in
                               ('opds_catalog_bookauthor', 'opds_catalog_bookgenre', 'opds_catalog_bookseries', 'opds_catalog_bookshelf'))]
        self.assertLessEqual(len(link_queries), 5, link_queries)

    def test_bookshelf_processor_without_n_plus_1(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        from opds_catalog.models import Book, bookshelf
        for book in Book.objects.all()[:4]:
            bookshelf.objects.create(user=self.user, book=book)
        config.SOPDS_AUTH = True
        c = Client()
        c.force_login(self.user)
        with CaptureQueriesContext(connection) as ctx:
            response = c.get(reverse('web:main'))
        self.assertEqual(response.status_code, 200)
        shelf_queries = [q['sql'] for q in ctx.captured_queries if 'opds_catalog_bookshelf' in q['sql']]
        self.assertLessEqual(len(shelf_queries), 1, shelf_queries)
        config.SOPDS_AUTH = False
