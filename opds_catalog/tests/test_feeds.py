# -*- coding: utf-8 -*-

from django.urls import reverse
from django.test import TestCase, Client
from django.utils.translation import gettext as _

from opds_catalog import opdsdb
from opds_catalog import settings
from constance import config


class feedsTestCase(TestCase):
    fixtures = ['testdb.json']
    
    def setUp(self):
        config.SOPDS_AUTH=False           
  
    def test_MainFeed(self):
        c = Client()
        response = c.get('/opds/')
        self.assertEqual(response.status_code, 200)
        response = c.get(reverse('opds:main'));
        self.assertEqual(response.status_code, 200)
        self.assertIn(_('By catalogs'), response.content.decode())
        self.assertIn(_("Catalogs: %(catalogs)s, books: %(books)s.")%{"catalogs":2, "books":4}, response.content.decode())
        self.assertIn(_("Authors: %(authors)s.")%{"authors":4}, response.content.decode())
        self.assertIn(_("Genres: %(genres)s.")%{"genres":4}, response.content.decode())
            
    def test_CatalogsFeed(self):
        c = Client()
        response = c.get('/opds/catalogs/')
        self.assertEqual(response.status_code, 200)
        response = c.get(reverse('opds:catalogs'));
        self.assertEqual(response.status_code, 200)  
        self.assertIn('books.zip', response.content.decode())
        self.assertIn('The Sanctuary Sparrow', response.content.decode())                   
       
    def test_CatalogsFeedTree(self):
        c = Client()
        response = c.get('/opds/catalogs/4/')
        self.assertEqual(response.status_code, 200)
        response = c.get( reverse('opds:cat_tree',args=['4']) )
        self.assertEqual(response.status_code, 200) 
        self.assertIn('Драконьи Услуги', response.content.decode())     
        self.assertIn('Китайски сладкиш с късметче', response.content.decode())  
        self.assertIn('Любовь в жизни Обломова', response.content.decode())  
        
    def test_OpenSearch(self):
        c = Client()
        response = c.get('/opds/search/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('www.sopds.ru', response.content.decode())
        
    def test_SearchTypes(self):
        c = Client()
        response = c.get('/opds/search/Драк/')
        self.assertEqual(response.status_code, 200)
        response = c.get(reverse('opds:searchtypes', kwargs={'searchterms':'Драк'}))
        self.assertEqual(response.status_code, 200)
        self.assertIn(_("Search by titles"), response.content.decode())
        
    def test_SearchBooks(self):
        c = Client()        
        response = c.get('/opds/search/books/m/Драк/')
        self.assertEqual(response.status_code, 200)
        response = c.get(reverse('opds:searchbooks', kwargs={'searchtype':'m','searchterms':'рак'}))
        self.assertEqual(response.status_code, 200)        
        self.assertIn("Драконьи Услуги", response.content.decode())
        self.assertIn("Куприянов Денис", response.content.decode())
        response = c.get(reverse('opds:searchbooks', kwargs={'searchtype':'b','searchterms':'Драк'}))
        self.assertEqual(response.status_code, 200)        
        self.assertIn("Драконьи Услуги", response.content.decode())
        self.assertIn("Куприянов Денис", response.content.decode())   
        response = c.get(reverse('opds:searchbooks', kwargs={'searchtype':'a','searchterms':'8'}))
        self.assertEqual(response.status_code, 200)        
        self.assertIn("Драконьи Услуги", response.content.decode())
        self.assertIn("Куприянов Денис", response.content.decode())  
        self.assertIn(_("All books by %(full_name)s")%{"full_name":"Куприянов Денис"}, response.content.decode())  
        self.assertIn("prose_contemporary", response.content.decode())    
        self.assertIn("<category ", response.content.decode()) 
    
    def test_SearchAuthors(self):
        c = Client()                
        response = c.get('/opds/search/authors/m/Логинов/')
        self.assertEqual(response.status_code, 200)
        response = c.get(reverse('opds:searchauthors', kwargs={'searchtype':'m','searchterms':'гинов'}))
        self.assertEqual(response.status_code, 200)        
        self.assertIn("Логинов Святослав", response.content.decode())     
        response = c.get(reverse('opds:searchauthors', kwargs={'searchtype':'b','searchterms':'Лог'}))
        self.assertEqual(response.status_code, 200)        
        self.assertIn("Логинов Святослав", response.content.decode())         

    def test_SearchGenres(self):        
        #response = c.get('/opds/search/genres/antiq/')
        #self.assertEqual(response.status_code, 200)
        #self.assertIn("The Sanctuary Sparrow", response.content.decode())
        #self.assertIn("Peters Ellis", response.content.decode())  
        pass  

    def test_LangFeed(self):
        c = Client()
        response = c.get('/opds/books/')
        self.assertEqual(response.status_code, 200)
        response = c.get(reverse('opds:lang_books'));
        self.assertEqual(response.status_code, 200)
        self.assertIn(_("Cyrillic"), response.content.decode())
        self.assertIn(_("Latin"), response.content.decode())
        self.assertIn(_("Digits"), response.content.decode())
        self.assertIn(_("Other symbols"), response.content.decode())  
        self.assertIn(_("Show all"), response.content.decode())           
     
    def test_BooksFeed(self):
        c = Client()
        response = c.get('/opds/books/0/')
        self.assertEqual(response.status_code, 200)
        if config.SOPDS_ALPHABET_MENU:
            response = c.get(reverse('opds:lang_books'));
            self.assertEqual(response.status_code, 200)
            self.assertIn(_("Cyrillic"), response.content.decode()) 
        response = c.get(reverse('opds:char_books', kwargs={'lang_code':0}));
        self.assertIn("<title>T</title>", response.content.decode())

    def test_AuthorsFeed(self):
        c = Client()
        response = c.get('/opds/authors/0/')
        self.assertEqual(response.status_code, 200)
        if config.SOPDS_ALPHABET_MENU:        
            response = c.get(reverse('opds:lang_authors'));
            self.assertEqual(response.status_code, 200)
            self.assertIn(_("Cyrillic"), response.content.decode())  
        response = c.get(reverse('opds:char_authors', kwargs={'lang_code':0}));    
        self.assertIn("<title>P</title>", response.content.decode())    
        
        
    def test_GenresFeed(self):
        c = Client()
        response = c.get('/opds/genres/')
        self.assertEqual(response.status_code, 200)
        response = c.get(reverse('opds:genres'));
        self.assertEqual(response.status_code, 200)
        self.assertIn(opdsdb.unknown_genre_en, response.content.decode()) 
        response = c.get(reverse('opds:genres', kwargs={'section':232}));
        self.assertEqual(response.status_code, 200)
        self.assertIn("prose_contemporary", response.content.decode())         


class feedInstanceStateTestCase(TestCase):
    fixtures = ['testdb.json']

    def setUp(self):
        config.SOPDS_AUTH = False

    def test_each_request_gets_own_feed_instance(self):
        from opds_catalog import feeds as feeds_module

        seen = []
        original_get_object = feeds_module.SearchSeriesFeed.get_object
        original_items = feeds_module.SearchSeriesFeed.items

        def tracked_get_object(self, request, *args, **kwargs):
            seen.append(('get_object', self))
            return original_get_object(self, request, *args, **kwargs)

        def tracked_items(self, obj):
            seen.append(('items', self))
            return original_items(self, obj)

        feeds_module.SearchSeriesFeed.get_object = tracked_get_object
        feeds_module.SearchSeriesFeed.items = tracked_items
        try:
            c = Client()
            r1 = c.get(reverse('opds:searchseries', kwargs={'searchtype': 'm', 'searchterms': 'Драк'}))
            r2 = c.get(reverse('opds:searchseries', kwargs={'searchtype': 'a', 'searchterms': '8'}))
        finally:
            feeds_module.SearchSeriesFeed.get_object = original_get_object
            feeds_module.SearchSeriesFeed.items = original_items

        self.assertEqual(r1.status_code, 200)
        self.assertEqual(r2.status_code, 200)

        go = [obj for tag, obj in seen if tag == 'get_object']
        it = [obj for tag, obj in seen if tag == 'items']
        self.assertEqual(len(go), 2)
        self.assertEqual(len(it), 2)
        self.assertIsNot(go[0], go[1], 'feed instance is shared between requests')
        self.assertIs(go[0], it[0], 'items() ran on a different instance than get_object()')
        self.assertIs(go[1], it[1], 'items() ran on a different instance than get_object()')

    def test_genre_feed_state_not_shared_between_requests(self):
        from opds_catalog import feeds as feeds_module

        seen = []
        original_item_link = feeds_module.GenresFeed.item_link

        def tracked_item_link(self, item):
            seen.append(self)
            return original_item_link(self, item)

        feeds_module.GenresFeed.item_link = tracked_item_link
        try:
            c = Client()
            c.get(reverse('opds:genres', kwargs={'section': 231}))
            c.get(reverse('opds:genres', kwargs={'section': 232}))
        finally:
            feeds_module.GenresFeed.item_link = original_item_link

        self.assertTrue(seen)
        self.assertIsNot(seen[0], seen[-1], 'genre feed instance shared between different sections')


class feedAuthTestCase(TestCase):
    fixtures = ['testdb.json']

    def setUp(self):
        config.SOPDS_AUTH = True
        from django.contrib.auth.models import User
        self.user = User.objects.create_user('tester', password='secret123')

    def tearDown(self):
        config.SOPDS_AUTH = False

    def _basic(self):
        import base64
        return 'Basic ' + base64.b64encode(b'tester:secret123').decode()

    def test_main_feed_denies_anonymous(self):
        response = Client().get('/opds/')
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response['WWW-Authenticate'], 'Basic realm="OPDS"')

    def test_main_feed_allows_basic_auth(self):
        response = Client().get('/opds/', HTTP_AUTHORIZATION=self._basic())
        self.assertEqual(response.status_code, 200)
        self.assertIn('SimpleOPDS', response.content.decode())

    def test_main_feed_allows_session_auth(self):
        c = Client()
        c.force_login(self.user)
        response = c.get('/opds/')
        self.assertEqual(response.status_code, 200)


class unknownGenreTestCase(TestCase):
    fixtures = ['testdb.json']

    def setUp(self):
        config.SOPDS_AUTH = False

    def test_unknown_genre_returns_404(self):
        response = Client().get(reverse('opds:genres', kwargs={'section': 99999}))
        self.assertEqual(response.status_code, 404)


class feedErrorHandlingTestCase(TestCase):
    fixtures = ['testdb.json']

    def setUp(self):
        config.SOPDS_AUTH = False

    def test_duplicates_feed_invalid_id_404(self):
        response = Client().get(reverse('opds:searchbooks', kwargs={'searchtype': 'd', 'searchterms': 'abc'}))
        self.assertEqual(response.status_code, 404)
        response = Client().get(reverse('opds:searchbooks', kwargs={'searchtype': 'd', 'searchterms': '999999'}))
        self.assertEqual(response.status_code, 404)

    def test_malformed_authorization_header_401_not_500(self):
        import base64
        config.SOPDS_AUTH = True
        try:
            for header in ('garbage', 'Basic %%%%', 'Basic ' + base64.b64encode(b'nocolon').decode()):
                response = Client().get('/opds/', HTTP_AUTHORIZATION=header)
                self.assertEqual(response.status_code, 401, header)
        finally:
            config.SOPDS_AUTH = False
