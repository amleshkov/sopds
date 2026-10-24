from datetime import datetime

from django.conf import settings as main_settings
from django.contrib.auth.models import User
from django.test import TestCase, TransactionTestCase
from django.utils import timezone

from opds_catalog import models, opdsdb
from opds_catalog.models import (
    Author,
    Book,
    BookAuthor,
    BookGenre,
    BookSeries,
    Catalog,
    Counter,
    Genre,
    Series,
    bookshelf,
)


class modelsTestCase(TestCase):
    testdatetime = datetime(2016, 1, 1, 0, 0)
    if main_settings.USE_TZ:
        testdatetime = testdatetime.replace(tzinfo=timezone.get_current_timezone())

    def setUp(self):
        opdsdb.clear_all()
        book = Book.objects.create(filename="testbook.fb2", path=".", filesize=500, format="fb2", cat_type=0, 
                            registerdate=self.testdatetime,docdate="01.01.2016", lang="ru", title="Книга", search_title="КНИГА", 
                            annotation="Аннотация", avail=2,catalog=Catalog.objects.create(parent=None, cat_name=".", path=".", cat_type=0)
        )
        author = Author.objects.create(full_name="Шелепнев Дмитрий", search_full_name="ШЕЛЕПНЕВ ДМИТРИЙ")
        genre = Genre.objects.create(genre="fantastic0", section="fantastic1", subsection="fantastic2")
        series = Series.objects.create(ser="mywork", search_ser="MYWORK")
        BookAuthor.objects.create(book=book, author=author)
        BookGenre.objects.create(book=book, genre=genre)
        BookSeries.objects.create(book=book, ser=series, ser_no=1)
        user = User.objects.create_user("testuser","testuser@sopds.ru", "testpassword", first_name="Test", last_name="User")
        bookshelf.objects.create(user=user, book=book, readtime=self.testdatetime)
        Counter.objects.update_known_counters()


    def test_Book(self):
        """ Тестирование соответствия структуры модели Book и работоспособности БД """
        book = Book.objects.get(title="Книга")
        self.assertEqual(book.filename, "testbook.fb2")
        self.assertEqual(book.path, ".")
        self.assertEqual(book.filesize, 500)
        self.assertEqual(book.format, "fb2")
        self.assertEqual(book.cat_type, 0)
        self.assertEqual(book.registerdate, self.testdatetime)
        self.assertEqual(book.docdate, "01.01.2016")
        self.assertEqual(book.lang, "ru")
        self.assertEqual(book.title, "Книга")
        self.assertEqual(book.search_title, "КНИГА")
        self.assertEqual(book.annotation, "Аннотация")
        self.assertEqual(book.avail, 2)
        self.assertEqual(book.catalog.path, ".")
        self.assertEqual(book.catalog.cat_name, ".")
        self.assertEqual(book.catalog.cat_type, 0)

    def test_Author(self):
        """ Тестирование соответствия структуры моделей Author и BookAuthor и работоспособности БД """
        book = Book.objects.get(title="Книга")
        self.assertEqual(book.authors.count(), 1)
        self.assertEqual(book.authors.get(full_name="Шелепнев Дмитрий").search_full_name, "ШЕЛЕПНЕВ ДМИТРИЙ")

    def test_Genre(self):
        """ Тестирование соответствия структуры моделей Genre и BookGenre и работоспособности БД """
        book = Book.objects.get(title="Книга")
        self.assertEqual(book.genres.count(), 1)
        self.assertEqual(book.genres.get(genre="fantastic0").section, "fantastic1")
        self.assertEqual(book.genres.get(genre="fantastic0").subsection, "fantastic2")

    def test_Series(self):
        """ Тестирование соответствия структуры моделей Series и BookSeries и работоспособности БД """
        book = Book.objects.get(title="Книга")
        self.assertEqual(book.series.count(), 1)
        ser = book.series.all()[0]
        self.assertEqual(ser.ser,"mywork")
        self.assertEqual(ser.search_ser,"MYWORK")
        self.assertEqual(BookSeries.objects.get(ser=ser).ser_no, 1)

    def test_bookshelf(self):
        """ Тестирование соответствия структуры модели bookshelf и работоспособности БД """
        user = User.objects.get(username="testuser")
        self.assertEqual(bookshelf.objects.all().count(), 1)
        self.assertEqual(bookshelf.objects.filter(user=user).count(), 1)
        self.assertEqual(bookshelf.objects.get(user=user).book.title, "Книга")

    def test_Counter(self):
        """ Тестирование соответствия структуры модели Counter, менеджера CounterManager и работоспособности БД """
        self.assertEqual(Counter.objects.get_counter(models.counter_allbooks), 1)
        self.assertEqual(Counter.objects.get_counter(models.counter_allauthors), 1)
        self.assertEqual(Counter.objects.get_counter(models.counter_allcatalogs), 1)
        self.assertEqual(Counter.objects.get_counter(models.counter_allgenres), 1)
        self.assertEqual(Counter.objects.get_counter(models.counter_allseries), 1)


class constraintsTestCase(TestCase):
    testdatetime = datetime(2016, 1, 1, 0, 0)
    if main_settings.USE_TZ:
        testdatetime = testdatetime.replace(tzinfo=timezone.get_current_timezone())

    def _make_book(self, catalog):
        return Book(filename="dup.fb2", path=".", filesize=1, format="fb2", cat_type=0,
                    registerdate=self.testdatetime, docdate="01.01.2016", lang="ru",
                    title="Дубль", search_title="ДУБЛЬ", annotation="", avail=2, catalog=catalog)

    def test_duplicate_book_filename_path_rejected(self):
        catalog = Catalog.objects.create(parent=None, cat_name=".", path=".")
        self._make_book(catalog).save()
        from django.db import IntegrityError, transaction
        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                self._make_book(catalog).save()

    def test_duplicate_catalog_path_rejected(self):
        Catalog.objects.create(parent=None, cat_name=".", path="dup_dir")
        from django.db import IntegrityError, transaction
        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                Catalog.objects.create(parent=None, cat_name=".", path="dup_dir")


class migrationDedupTestCase(TransactionTestCase):

    def test_dedup_migration_removes_duplicates_and_cascades_links(self):
        from django.apps import apps as global_apps
        from django.db import connection
        from django.db.migrations.executor import MigrationExecutor

        executor = MigrationExecutor(connection)
        target_back = ('opds_catalog', '0005_auto_20161204_2138')
        executor.migrate([target_back])
        executor.loader.build_graph()
        old_apps = executor.loader.project_state(target_back).apps

        OldBook = old_apps.get_model('opds_catalog', 'Book')
        OldCatalog = old_apps.get_model('opds_catalog', 'Catalog')
        OldAuthor = old_apps.get_model('opds_catalog', 'Author')
        OldLink = old_apps.get_model('opds_catalog', 'bauthor')

        cat = OldCatalog.objects.create(parent=None, cat_name='.', path='.')
        OldCatalog.objects.create(parent=None, cat_name='.', path='.')

        common = dict(path='.', filesize=1, format='fb2', catalog=cat,
                      registerdate=self.__class__.testdatetime if hasattr(self.__class__, 'testdatetime') else '2016-01-01T00:00:00Z',
                      docdate='01.01.2016', lang='ru', title='Книга', search_title='КНИГА',
                      annotation='', avail=2, cat_type=0)
        first = OldBook.objects.create(filename='dup.fb2', **common)
        second = OldBook.objects.create(filename='dup.fb2', **common)

        author = OldAuthor.objects.create(full_name='Автор', search_full_name='АВТОР')
        OldLink.objects.create(book=first, author=author)
        OldLink.objects.create(book=second, author=author)

        executor.migrate([('opds_catalog', '0007_alter_author_full_name_alter_author_search_full_name_and_more')])

        Book = global_apps.get_model('opds_catalog', 'Book')
        Catalog = global_apps.get_model('opds_catalog', 'Catalog')
        BookAuthor = global_apps.get_model('opds_catalog', 'BookAuthor')

        self.assertEqual(Book.objects.filter(filename='dup.fb2', path='.').count(), 1)
        self.assertEqual(Catalog.objects.filter(path='.').count(), 1)
        kept = Book.objects.get(filename='dup.fb2', path='.')
        self.assertEqual(kept.id, min(first.id, second.id))
        self.assertEqual(BookAuthor.objects.filter(book_id=second.id).count(), 0)
        self.assertEqual(BookAuthor.objects.filter(book_id=first.id).count(), 1)
