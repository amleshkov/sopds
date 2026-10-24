# -*- coding: utf-8 -*-

import io
import logging
import os
from functools import wraps

from django.http import FileResponse, Http404, HttpResponse
from django.views.decorators.cache import cache_page
from PIL import Image

import opds_catalog.zipf as zipfile
from book_tools.format import create_bookfile, mime_detector
from book_tools.format.mimetype import Mimetype
from constance import config
from opds_catalog import opdsdb, settings, utils
from opds_catalog.middleware import sopds_auth_required
from opds_catalog.models import Book, bookshelf

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


def book_full_path(book):
    full_path = os.path.join(config.SOPDS_ROOT_LIB, book.path)
    if book.cat_type == opdsdb.CAT_INP:
        inp_path, zip_name = os.path.split(full_path)
        inpx_path, inp_name = os.path.split(inp_path)
        path, inpx_name = os.path.split(inpx_path)
        full_path = os.path.join(path, zip_name)
    return full_path


class BookStream:
    """File-like wrapper around the book bytes plus every resource that must be closed with it."""

    def __init__(self, stream, resources):
        self._stream = stream
        self._resources = resources

    def read(self, size=-1):
        return self._stream.read(size)

    def __getattr__(self, name):
        return getattr(self._stream, name)

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        self.close()

    def close(self):
        for resource in self._resources:
            try:
                resource.close()
            except Exception as err:
                logger.debug('Error closing book stream resource: %s', err)


def open_book_stream(book):
    """Open the raw bytes of a book file for streaming. Raises Http404 when unavailable."""
    full_path = book_full_path(book)
    try:
        if book.cat_type == opdsdb.CAT_NORMAL:
            fo = open(os.path.join(full_path, book.filename), 'rb')
            return BookStream(fo, [fo])
        if book.cat_type in (opdsdb.CAT_ZIP, opdsdb.CAT_INP):
            fz = open(full_path, 'rb')
            try:
                z = zipfile.ZipFile(fz, 'r', allowZip64=True)
                fo = z.open(book.filename)
            except Exception:
                fz.close()
                raise
            return BookStream(fo, [fo, z, fz])
    except (OSError, KeyError, RuntimeError, zipfile.BadZipFile) as err:
        logger.warning('Book file not available (book %s): %s', book.id, err)
        raise Http404
    raise Http404


@sopds_auth_required
def Download(request, book_id, zip_flag):
    """ Загрузка файла книги """
    try:
        book = Book.objects.get(id=book_id)
    except Book.DoesNotExist:
        raise Http404

    if config.SOPDS_AUTH and request.user.is_authenticated:
        bookshelf.objects.get_or_create(user=request.user, book=book)

    transname = getFileName(book)

    if zip_flag == '1':
        dlfilename = transname + '.zip'
        content_type = Mimetype.FB2_ZIP if book.format == 'fb2' else Mimetype.ZIP
    else:
        dlfilename = transname
        content_type = mime_detector.fmt(book.format)

    headers = {
        "Content-Type": '%s; name="%s"' % (content_type, dlfilename),
        "Content-Disposition": 'attachment; filename="%s"' % dlfilename,
        "Content-Transfer-Encoding": 'binary',
    }

    stream = open_book_stream(book)

    if zip_flag == '1':
        dio = io.BytesIO()
        with zipfile.ZipFile(dio, 'w', zipfile.ZIP_DEFLATED) as zo:
            zo.writestr(transname, stream.read())
        stream.close()
        buf = dio.getvalue()
        response = HttpResponse(content_type=headers["Content-Type"])
        for name, value in headers.items():
            response[name] = value
        response["Content-Length"] = str(len(buf))
        response.write(buf)
        return response

    response = FileResponse(stream, content_type=headers["Content-Type"])
    for name, value in headers.items():
        response[name] = value
    response["Content-Length"] = str(book.filesize)
    return response

@sopds_auth_required
@cover_cache
def Cover(request, book_id, thumbnail=False):
    """ Загрузка обложки """
    try:
        book = Book.objects.get(id=book_id)
    except Book.DoesNotExist:
        raise Http404
    response = HttpResponse()

    stream = open_book_stream(book)
    try:
        with stream:
            book_data = create_bookfile(stream, book.filename)
            image = book_data.extract_cover_memory() if book_data else None
    except Exception as err:
        logger.debug('Cover extraction failed for book %s: %s', book_id, err)
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
