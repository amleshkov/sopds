import os
import zipfile
from io import BytesIO
from xml import sax

from book_tools.format.fb2 import FB2, FB2Zip
from book_tools.format.fb2sax import FB2sax
from book_tools.format.mimetype import Mimetype
from book_tools.format.util import list_zip_file_infos
from constance import config


class mime_detector:
    @staticmethod
    def fmt(fmt):
        if fmt.lower() == 'xml':
            return Mimetype.XML
        elif fmt.lower() == 'fb2':
            return Mimetype.FB2
        elif fmt.lower() == 'zip':
            return Mimetype.ZIP
        else:
            return Mimetype.OCTET_STREAM

    @staticmethod
    def file(filename):
        (n, e) = os.path.splitext(filename)
        return mime_detector.fmt(e[1:])


def detect_mime(file, original_filename):
    FB2_ROOT = 'FictionBook'
    mime = mime_detector.file(original_filename)

    try:
        if mime == Mimetype.XML:
            if FB2_ROOT == __xml_root_tag(file):
                return Mimetype.FB2
        elif mime == Mimetype.ZIP:
            with zipfile.ZipFile(file) as zip_file:
                if not zip_file.testzip():
                    infolist = list_zip_file_infos(zip_file)
                    if len(infolist) == 1:
                        if FB2_ROOT == __xml_root_tag(zip_file.open(infolist[0])):
                            return Mimetype.FB2_ZIP
    except Exception:
        pass

    return mime


def create_bookfile(file, original_filename):
    """Return a parsed book object for supported formats (fb2, fb2-in-zip), None otherwise."""
    if isinstance(file, str):
        file = open(file, 'rb')
    file = BytesIO(file.read())
    mimetype = detect_mime(file, original_filename)
    if mimetype == Mimetype.FB2:
        return FB2sax(file, original_filename) if config.SOPDS_FB2SAX else FB2(file, original_filename)
    if mimetype == Mimetype.FB2_ZIP:
        return FB2Zip(file, original_filename)
    return None


def __xml_root_tag(file):
    class XMLRootFound(Exception):
        def __init__(self, name):
            self.name = name

    class RootTagFinder(sax.handler.ContentHandler):
        def startElement(self, name, attributes):
            raise XMLRootFound(name)

    try:
        sax.parse(file, RootTagFinder())
    except XMLRootFound as e:
        return e.name
    return None
