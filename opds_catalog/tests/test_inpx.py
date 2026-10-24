# -*- coding: utf-8 -*-
import io
import os
import tempfile
import zipfile

from django.test import TestCase

from constance import config
from opds_catalog.models import Book, Catalog
from opds_catalog.sopdscan import opdsScanner

SEPARATOR = b'\x04'


def make_inpx(path, inp_name='test.inp', folder='anthology.zip'):
    structure = 'AUTHOR;GENRE;TITLE;SERIES;SERNO;FILE;SIZE;LIBID;DEL;EXT;DATE;LANG;FOLDER'
    book1 = SEPARATOR.join([
        'Пушкин Александр:Другой Автор'.encode('utf-8'),
        b'poetry',
        'Сказка о тесте'.encode('utf-8'),
        b'',
        b'0',
        b'pushkin_test',
        b'1000',
        b'1',
        b'0',
        b'fb2',
        b'2020-01-01',
        b'ru',
        folder.encode('utf-8'),
    ])
    deleted = SEPARATOR.join([
        'Удалённый Автор'.encode('utf-8'),
        b'poetry',
        'Удалённая книга'.encode('utf-8'),
        b'',
        b'0',
        b'deleted_book',
        b'1000',
        b'2',
        b'1',
        b'fb2',
        b'2020-01-01',
        b'ru',
        folder.encode('utf-8'),
    ])
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w') as zf:
        zf.writestr('structure.info', structure)
        zf.writestr(inp_name, book1 + b'\n' + deleted + b'\n')
    with open(path, 'wb') as f:
        f.write(buf.getvalue())


class inpxScanTestCase(TestCase):

    def setUp(self):
        self.lib = tempfile.TemporaryDirectory()
        self.addCleanup(self.lib.cleanup)
        lib = self.lib.name
        os.makedirs(os.path.join(lib, 'inpxdir'))
        make_inpx(os.path.join(lib, 'inpxdir', 'test.inpx'))

        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, 'w') as zf:
            with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', '262001.fb2'), 'rb') as f:
                zf.writestr('pushkin_test.fb2', f.read())
        with open(os.path.join(lib, 'inpxdir', 'anthology.zip'), 'wb') as f:
            f.write(zip_buf.getvalue())

        config.SOPDS_ROOT_LIB = lib
        config.SOPDS_INPX_ENABLE = True
        config.SOPDS_AUTH = False

    def tearDown(self):
        config.SOPDS_INPX_ENABLE = False

    def test_inpx_scan_adds_books(self):
        scanner = opdsScanner()
        scanner.scan_all()

        self.assertEqual(scanner.books_added, 1)
        self.assertEqual(Book.objects.count(), 1)

        book = Book.objects.get(filename='pushkin_test.fb2')
        self.assertEqual(book.title, 'Сказка о тесте')
        self.assertEqual(book.lang, 'ru')
        self.assertEqual(book.docdate, '2020-01-01')
        self.assertEqual(book.cat_type, 3)
        self.assertEqual(book.path, os.path.join('inpxdir', 'test.inpx', 'test.inp', 'anthology.zip'))
        self.assertEqual(book.authors.count(), 2)
        self.assertEqual(book.authors.filter(full_name='Пушкин Александр').count(), 1)
        self.assertEqual(book.genres.get(genre='poetry').subsection, 'poetry')

        catalog = Catalog.objects.get(parent__path=os.path.join('inpxdir', 'test.inpx', 'test.inp'))
        self.assertEqual(catalog.cat_type, 3)

    def test_inpx_rescan_skips_unchanged(self):
        config.SOPDS_INPX_SKIP_UNCHANGED = True
        scanner = opdsScanner()
        scanner.scan_all()
        scanner = opdsScanner()
        scanner.scan_all()
        self.assertEqual(Book.objects.count(), 1)
        self.assertEqual(Book.objects.get(filename='pushkin_test.fb2').avail, 2)
        config.SOPDS_INPX_SKIP_UNCHANGED = False

    def test_inpx_book_download(self):
        from django.test import Client
        from django.urls import reverse
        scanner = opdsScanner()
        scanner.scan_all()

        book = Book.objects.get(filename='pushkin_test.fb2')
        response = Client().get(reverse('opds:download', kwargs={'book_id': book.id, 'zip_flag': 0}))
        self.assertEqual(response.status_code, 200)
        content = b''.join(response.streaming_content)
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, 'w') as zf:
            with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', '262001.fb2'), 'rb') as f:
                zf.writestr('pushkin_test.fb2', f.read())
        with zipfile.ZipFile(io.BytesIO(zip_buf.getvalue())) as zf:
            self.assertEqual(content, zf.read('pushkin_test.fb2'))
