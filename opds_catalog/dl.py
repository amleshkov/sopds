# -*- coding: utf-8 -*-

import logging
import os
import codecs
import io
from functools import wraps

from django.http import HttpResponse, Http404
from django.views.decorators.cache import cache_page

from opds_catalog.models import Book, bookshelf
from opds_catalog import settings, utils, opdsdb
from opds_catalog.middleware import sopds_auth_required
import opds_catalog.zipf as zipfile

from book_tools.format import create_bookfile, mime_detector
from book_tools.format.mimetype import Mimetype

from constance import config
from PIL import Image

logger = logging.getLogger(__name__)


def cover_cache(view):
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        return cache_page(config.SOPDS_CACHE_TIME)(view)(request, *args, **kwargs)
    return wrapper


def getFileName(book):
    if config.SOPDS_TITLE_AS_FILENAME:
        transname = utils.translit(book.title + '.' + book.format)
    else:
        transname = utils.translit(book.filename)

    return utils.to_ascii(transname)


@sopds_auth_required
def Download(request, book_id, zip_flag):
    """ Загрузка файла книги """
    try:
        book = Book.objects.get(id=book_id)
    except Book.DoesNotExist:
        raise Http404

    if config.SOPDS_AUTH and request.user.is_authenticated:
        bookshelf.objects.get_or_create(user=request.user, book=book)

    full_path=os.path.join(config.SOPDS_ROOT_LIB,book.path)
    
    if book.cat_type==opdsdb.CAT_INP:
        # Убираем из пути INPX и INP файл
        inp_path, zip_name = os.path.split(full_path)
        inpx_path, inp_name = os.path.split(inp_path)
        path, inpx_name = os.path.split(inpx_path)
        full_path = os.path.join(path,zip_name)
        
    if config.SOPDS_TITLE_AS_FILENAME:
        transname=utils.translit(book.title+'.'+book.format)
    else:
        transname=utils.translit(book.filename)
        
    transname = utils.to_ascii(transname)
        
    if zip_flag == '1':
        dlfilename=transname+'.zip'   
        content_type= Mimetype.FB2_ZIP if book.format=='fb2' else Mimetype.ZIP
    else:    
        dlfilename=transname
        content_type = mime_detector.fmt(book.format)

    response = HttpResponse()
    response["Content-Type"]='%s; name="%s"'%(content_type,dlfilename)
    response["Content-Disposition"] = 'attachment; filename="%s"'%(dlfilename)
    response["Content-Transfer-Encoding"]='binary'

    z = None
    fz = None
    fo = None
    s = None
    book_size = book.filesize
    try:
        if book.cat_type==opdsdb.CAT_NORMAL:
            file_path=os.path.join(full_path, book.filename)
            book_size=os.path.getsize(file_path)
            fo=codecs.open(file_path, "rb")
            s=fo.read()
        elif book.cat_type in [opdsdb.CAT_ZIP, opdsdb.CAT_INP]:
            fz=codecs.open(full_path, "rb")
            z = zipfile.ZipFile(fz, 'r', allowZip64=True)
            book_size=z.getinfo(book.filename).file_size
            fo= z.open(book.filename)
            s=fo.read()
    except (OSError, KeyError, zipfile.BadZipFile):
        raise Http404

    if zip_flag=='1':
        dio = io.BytesIO()
        zo = zipfile.ZipFile(dio, 'w', zipfile.ZIP_DEFLATED)
        zo.writestr(transname,s)
        zo.close()
        buf = dio.getvalue()
        response["Content-Length"] = str(len(buf))
        response.write(buf)        
    else:
        response["Content-Length"] = str(book_size)
        response.write(s)

    if fo: fo.close()
    if z: z.close()
    if fz: fz.close()

    return response

# Новая версия (0.42) процедуры извлечения обложек из файлов книг fb2, epub, mobi
@sopds_auth_required
@cover_cache
def Cover(request, book_id, thumbnail=False):
    """ Загрузка обложки """
    try:
        book = Book.objects.get(id=book_id)
    except Book.DoesNotExist:
        raise Http404
    response = HttpResponse()
    full_path = os.path.join(config.SOPDS_ROOT_LIB, book.path)
    if book.cat_type == opdsdb.CAT_INP:
        # Убираем из пути INPX и INP файл
        inp_path, zip_name = os.path.split(full_path)
        inpx_path, inp_name = os.path.split(inp_path)
        path, inpx_name = os.path.split(inpx_path)
        full_path = os.path.join(path,zip_name)

    try:
        if book.cat_type == opdsdb.CAT_NORMAL:
            file_path = os.path.join(full_path, book.filename)
            fo = codecs.open(file_path, "rb")
            book_data = create_bookfile(fo,book.filename)
            image = book_data.extract_cover_memory()
            #fb2.parse(fo, 0)
            fo.close()
        elif book.cat_type in [opdsdb.CAT_ZIP, opdsdb.CAT_INP]:
            fz = codecs.open(full_path, "rb")
            z = zipfile.ZipFile(fz, 'r', allowZip64=True)
            fo = z.open(book.filename)
            book_data = create_bookfile(fo, book.filename)
            image = book_data.extract_cover_memory()
            #fb2.parse(fo, 0)
            fo.close()
            z.close()
            fz.close()
    except Exception as err:
        logger.debug('Cover extraction failed for book %s: %s', book_id, err)
        book_data = None
        image = None

    if image:
        response["Content-Type"] = 'image/jpeg'
        if thumbnail:
            thumb = Image.open(io.BytesIO(image)).convert('RGB')
            thumb.thumbnail((settings.THUMB_SIZE, settings.THUMB_SIZE), Image.LANCZOS)
            tfile = io.BytesIO()
            thumb.save(tfile, 'JPEG')
            image = tfile.getvalue()
        response.write(image)

    if not image:
        try:
            with open(config.SOPDS_NOCOVER_PATH, "rb") as f:
                response["Content-Type"] = 'image/jpeg'
                response.write(f.read())
        except OSError:
            raise Http404

    return response

@sopds_auth_required
def Thumbnail(request, book_id):
    return Cover(request, book_id, True)
