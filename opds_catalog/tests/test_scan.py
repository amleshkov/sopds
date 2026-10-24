import os
import shutil
import tempfile

from django.test import TestCase

from constance import config
from opds_catalog import opdsdb

#from opds_catalog import settings
from opds_catalog.models import Author, Book, Catalog, Genre, Series
from opds_catalog.sopdscan import opdsScanner


class scanTestCase(TestCase):
    test_module_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    test_ROOTLIB = os.path.join(test_module_path, 'tests/data')
    test_fb2 = "262001.fb2"
    test_epub = "mirer.epub"
    test_mobi = "robin_cook.mobi"
    test_zip = "books.zip"

    def setUp(self):
        config.SOPDS_ROOT_LIB = self.test_ROOTLIB

    def test_processfile_fb2(self):
        """ Тестирование процедуры processfile (извлекает метаданные из книги FB2 и помещает в БД) """
        opdsdb.clear_all()
        scanner = opdsScanner()
        scanner.processfile(self.test_fb2, self.test_ROOTLIB, os.path.join(self.test_ROOTLIB,self.test_fb2), None,0,495373)
        book = Book.objects.get(filename=self.test_fb2)
        self.assertIsNotNone(book)
        self.assertEqual(scanner.books_added,1)
        self.assertEqual(book.filename, self.test_fb2)
        self.assertEqual(book.path, ".")
        self.assertEqual(book.format, "fb2")
        self.assertEqual(book.cat_type, 0)
        #self.assertGreaterEqual(book.registerdate, )
        self.assertEqual(book.docdate, "30.1.2011")
        self.assertEqual(book.lang, "en")
        self.assertEqual(book.title, "The Sanctuary Sparrow")
        self.assertEqual(book.search_title, "The Sanctuary Sparrow".upper())
        self.assertEqual(book.annotation, "")
        self.assertEqual(book.avail, 2)
        self.assertEqual(book.catalog.path, ".")
        self.assertEqual(book.catalog.cat_name, ".")
        self.assertEqual(book.catalog.cat_type, 0)
        self.assertEqual(book.filesize, 495373)

        self.assertEqual(book.authors.count(), 1)
        self.assertEqual(book.authors.get(full_name="Peters Ellis").search_full_name, "PETERS ELLIS")

        self.assertEqual(book.genres.count(), 1)
        self.assertEqual(book.genres.get(genre="antique").section, opdsdb.unknown_genre)
        self.assertEqual(book.genres.get(genre="antique").subsection, "antique")

    def test_processfile_fb2sax(self):
        config.SOPDS_FB2SAX = True
        self.test_processfile_fb2()

    def test_processfile_fb2xpath(self):
        config.SOPDS_FB2SAX = False
        self.test_processfile_fb2()

    def test_processfile_epub(self):
        """ Тестирование процедуры processfile (извлекает метаданные из книги EPUB и помещает в БД) """
        opdsdb.clear_all()
        scanner = opdsScanner()
        scanner.processfile(self.test_epub, self.test_ROOTLIB, os.path.join(self.test_ROOTLIB,self.test_epub), None,0,491279)
        book = Book.objects.get(filename=self.test_epub)
        self.assertIsNotNone(book)
        self.assertEqual(scanner.books_added,1)
        self.assertEqual(book.filename, self.test_epub)
        self.assertEqual(book.path, ".")
        self.assertEqual(book.format, "epub")
        self.assertEqual(book.cat_type, 0)
        #self.assertGreaterEqual(book.registerdate, )
        self.assertEqual(book.docdate, "2015")
        self.assertEqual(book.lang, "ru")
        self.assertEqual(book.title, "У меня девять жизней (шф (продолжатели))")
        self.assertEqual(book.search_title, "У меня девять жизней (шф (продолжатели))".upper())
        self.assertEqual(book.annotation, "Собрание произведений. Том 2")
        self.assertEqual(book.avail, 2)
        self.assertEqual(book.catalog.path, ".")
        self.assertEqual(book.catalog.cat_name, ".")
        self.assertEqual(book.catalog.cat_type, 0)
        self.assertEqual(book.filesize, 491279)

        self.assertEqual(book.authors.count(), 1)
        self.assertEqual(book.authors.get(full_name="Мирер Александр").search_full_name, "МИРЕР АЛЕКСАНДР")

        self.assertEqual(book.genres.count(), 1)
        self.assertEqual(book.genres.get(genre="sf").section, opdsdb.unknown_genre)
        self.assertEqual(book.genres.get(genre="sf").subsection, "sf")

    def test_processfile_mobi(self):
        """ Тестирование процедуры processfile (извлекает метаданные из книги EPUB и помещает в БД) """
        opdsdb.clear_all()
        scanner = opdsScanner()
        scanner.processfile(self.test_mobi, self.test_ROOTLIB, os.path.join(self.test_ROOTLIB,self.test_mobi), None,0,542811)
        book = Book.objects.get(filename=self.test_mobi)
        self.assertIsNotNone(book)
        self.assertEqual(scanner.books_added,1)
        self.assertEqual(book.filename, self.test_mobi)
        self.assertEqual(book.path, ".")
        self.assertEqual(book.format, "mobi")
        self.assertEqual(book.cat_type, 0)
        #self.assertGreaterEqual(book.registerdate, )
        self.assertEqual(book.docdate, "2011-11-20")
        self.assertEqual(book.lang, "")
        self.assertEqual(book.title, "Vector")
        self.assertEqual(book.search_title, "Vector".upper())
        self.assertEqual(book.annotation, "")
        self.assertEqual(book.avail, 2)
        self.assertEqual(book.catalog.path, ".")
        self.assertEqual(book.catalog.cat_name, ".")
        self.assertEqual(book.catalog.cat_type, 0)
        self.assertEqual(book.filesize, 542811)

        self.assertEqual(book.authors.count(), 1)
        self.assertEqual(book.authors.get(full_name="Cook Robin").search_full_name, "COOK ROBIN")

    def test_processzip(self):
        """ Тестирование процедуры processzip (извлекает метаданные из книг, помещенных в архив и помещает их БД) """
        opdsdb.clear_all()
        scanner = opdsScanner()
        scanner.processzip(self.test_zip, self.test_ROOTLIB, os.path.join(self.test_ROOTLIB,self.test_zip) )
        self.assertEqual(scanner.books_added, 3)
        self.assertEqual(Book.objects.all().count(), 3)
        self.assertEqual(Catalog.objects.all().count(), 2)

        book = Book.objects.get(filename="539603.fb2")
        self.assertEqual(book.filesize, 15194)
        self.assertEqual(book.path, self.test_zip)
        self.assertEqual(book.cat_type, 1)
        self.assertEqual(book.catalog.path, self.test_zip)
        self.assertEqual(book.catalog.cat_name, self.test_zip)
        self.assertEqual(book.catalog.cat_type, 1)
        self.assertEqual(book.docdate, "2014-09-15")
        self.assertEqual(book.title, "Любовь в жизни Обломова")
        self.assertEqual(book.avail, 2)
        self.assertEqual(book.authors.count(), 1)
        self.assertEqual(book.authors.get(full_name="Логинов Святослав").search_full_name, "ЛОГИНОВ СВЯТОСЛАВ")
        self.assertEqual(book.genres.count(), 1)
        self.assertEqual(book.genres.get(genre="nonf_criticism").section, opdsdb.unknown_genre)
        self.assertEqual(book.genres.get(genre="nonf_criticism").subsection, "nonf_criticism")

        book = Book.objects.get(filename="539485.fb2")
        self.assertEqual(book.filesize, 12293)
        self.assertEqual(book.path, self.test_zip)
        self.assertEqual(book.cat_type, 1)
        self.assertEqual(book.title, "Китайски сладкиш с късметче")
        self.assertEqual(book.authors.get(full_name="Фрич Чарлз").search_full_name, "ФРИЧ ЧАРЛЗ")

        book = Book.objects.get(filename="539273.fb2")
        self.assertEqual(book.filesize, 21722)
        self.assertEqual(book.path, self.test_zip)
        self.assertEqual(book.cat_type, 1)
        self.assertEqual(book.title, "Драконьи Услуги")
        self.assertEqual(book.authors.get(full_name="Куприянов Денис").search_full_name, "КУПРИЯНОВ ДЕНИС")

    def test_scanall(self):
        """ Тестирование процедуры scanall (извлекает метаданные из книг и помещает в БД) """
        opdsdb.clear_all()
        scanner = opdsScanner()
        scanner.scan_all()
        self.assertEqual(scanner.books_added, 6)
        self.assertEqual(scanner.bad_books, 1)
        self.assertEqual(Book.objects.all().count(), 6)
        self.assertEqual(Author.objects.all().count(), 6)
        self.assertEqual(Genre.objects.all().count(), 5)
        self.assertEqual(Series.objects.all().count(), 1)
        self.assertEqual(Catalog.objects.all().count(), 2)


class scanResilienceTestCase(TestCase):
    test_module_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    test_ROOTLIB = os.path.join(test_module_path, 'tests/data')

    def setUp(self):
        config.SOPDS_ROOT_LIB = self.test_ROOTLIB

    def _scan(self, scanner):
        scanner.scan_all()

    def test_logical_delete_hides_and_restores_book(self):
        with tempfile.TemporaryDirectory() as lib:
            shutil.copy(os.path.join(self.test_ROOTLIB, '262001.fb2'), lib)
            shutil.copy(os.path.join(self.test_ROOTLIB, 'books.zip'), lib)
            config.SOPDS_ROOT_LIB = lib
            config.SOPDS_DELETE_LOGICAL = False

            scanner = opdsScanner()
            self._scan(scanner)
            self.assertEqual(Book.objects.count(), 4)

            os.remove(os.path.join(lib, '262001.fb2'))
            config.SOPDS_DELETE_LOGICAL = True
            scanner = opdsScanner()
            self._scan(scanner)

            self.assertEqual(Book.objects.count(), 3)
            self.assertEqual(Book.all_objects.count(), 4)
            ghost = Book.all_objects.get(filename='262001.fb2')
            self.assertEqual(ghost.avail, 0)

            shutil.copy(os.path.join(self.test_ROOTLIB, '262001.fb2'), lib)
            scanner = opdsScanner()
            self._scan(scanner)
            self.assertEqual(Book.objects.count(), 4)
            self.assertEqual(Book.objects.get(filename='262001.fb2').avail, 2)

    def test_symlink_loop_does_not_hang_scan(self):
        with tempfile.TemporaryDirectory() as lib:
            shutil.copy(os.path.join(self.test_ROOTLIB, '262001.fb2'), lib)
            os.symlink(lib, os.path.join(lib, 'loop'))
            config.SOPDS_ROOT_LIB = lib

            scanner = opdsScanner()
            self._scan(scanner)
            self.assertEqual(Book.objects.count(), 1)

    def test_batch_failure_keeps_committed_batches(self):
        from opds_catalog import sopdscan as sopdscan_module

        with tempfile.TemporaryDirectory() as lib:
            for name in ('a.fb2', 'b.fb2', 'c.fb2'):
                shutil.copy(os.path.join(self.test_ROOTLIB, '262001.fb2'), os.path.join(lib, name))
            config.SOPDS_ROOT_LIB = lib

            scanner = opdsScanner()
            original_processfile = scanner.processfile
            def flaky(name, *args, **kwargs):
                if name == 'b.fb2':
                    raise RuntimeError('boom')
                return original_processfile(name, *args, **kwargs)
            scanner.processfile = flaky

            old_batch = sopdscan_module.BATCH_SIZE
            sopdscan_module.BATCH_SIZE = 1
            try:
                self._scan(scanner)
            finally:
                sopdscan_module.BATCH_SIZE = old_batch

            self.assertEqual(Book.objects.count(), 2)
            self.assertFalse(Book.objects.filter(filename='b.fb2').exists())

    def test_scan_is_active_reset_after_failure(self):
        import logging
        from unittest import mock

        from opds_catalog.management.commands.sopds_scanner import Command
        cmd = Command()
        cmd.logger = logging.getLogger('')
        with mock.patch('opds_catalog.management.commands.sopds_scanner.opdsScanner') as mocked:
            mocked.return_value.scan_all.side_effect = RuntimeError('boom')
            with self.assertRaises(RuntimeError):
                cmd.scan()
        self.assertFalse(cmd.scan_is_active)
