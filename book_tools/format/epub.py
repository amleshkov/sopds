import os
import shutil
import urllib
import zipfile

from lxml import etree

from book_tools.format.bookfile import BookFile
from book_tools.format.mimetype import Mimetype


class EPub(BookFile):
    class Issue(object):
        FIRST_ITEM_NOT_MIMETYPE = 1
        MIMETYPE_ITEM_IS_DEFLATED = 2

    class Namespace(object):
        XHTML = 'http://www.w3.org/1999/xhtml'
        CONTAINER = 'urn:oasis:names:tc:opendocument:xmlns:container'
        OPF = 'http://www.idpf.org/2007/opf'
        DUBLIN_CORE = 'http://purl.org/dc/elements/1.1/'
        ENCRYPTION = 'http://www.w3.org/2001/04/xmlenc#'
        DIGITAL_SIGNATURE = 'http://www.w3.org/2000/09/xmldsig#'
        MARLIN = 'http://marlin-drm.com/epub'
        CALIBRE = 'http://calibre.kovidgoyal.net/2009/metadata'

    class Entry(object):
        MIMETYPE = 'mimetype'
        MANIFEST = 'META-INF/manifest.xml'
        METADATA = 'META-INF/metadata.xml'
        CONTAINER = 'META-INF/container.xml'
        ENCRYPTION = 'META-INF/encryption.xml'
        RIGHTS = 'META-INF/rights.xml'
        SIGNATURES = 'META-INF/signatures.xml'

    TOKEN_URL = 'https://books.fbreader.org/drm/marlin/get-token'
    CONTENT_ID_PREFIX = 'urn:marlin:organization:fbreader.org:0001:'

    ALGORITHM_EMBEDDING = 'http://www.idpf.org/2008/embedding'
    ALGORITHM_AES128 = Namespace.ENCRYPTION + 'aes128-cbc'

    class StructureException(Exception):
        def __init__(self, message):
            Exception.__init__(self, 'ePub verification failed: ' + message)

    def __init__(self, file, original_filename):
        BookFile.__init__(self, file, original_filename, Mimetype.EPUB)
        self.root_filename = None
        self.cover_fileinfos = []

        self.__zip_file = None
        self.__initialize()

    def __initialize(self):
        self.file.seek(0,0)
        self.__zip_file = zipfile.ZipFile(self.file)
        self.issues = []
        try:
            if self.__zip_file.testzip():
                raise EPub.StructureException('broken zip archive')

            infos = self.__zip_file.infolist()
            if len(infos) == 0:
                raise EPub.StructureException('empty zip archive')

            mimetype_info = infos[0]
            if mimetype_info.filename != EPub.Entry.MIMETYPE:
                self.issues.append(EPub.Issue.FIRST_ITEM_NOT_MIMETYPE)
            elif mimetype_info.compress_type != zipfile.ZIP_STORED:
                self.issues.append(EPub.Issue.MIMETYPE_ITEM_IS_DEFLATED)

            with self.__zip_file.open(EPub.Entry.MIMETYPE) as mimetype_file:
                if mimetype_file.read(30).decode().rstrip('\n\r') != Mimetype.EPUB:
                    raise EPub.StructureException('\'mimetype\' item content is incorrect')

            self.__extract_metainfo()
        except EPub.StructureException as error:
            self.close()
            raise error
        except Exception as error:
            self.close()
            raise EPub.StructureException(error.message)

    def close(self):
        self.__zip_file.close()

    def __exit__(self, kind, value, traceback):
        self.__zip_file.__exit__(kind, value, traceback)

    def __etree_from_entry(self, info):
        with self.__zip_file.open(info) as entry:
            try:
                return etree.fromstring(entry.read(1048576))
            except Exception:
                raise EPub.StructureException('\'' + info.filename + '\' is not a valid XML')

    def __extract_metainfo(self):
        root_info = self.__get_root_info()
        self.root_filename = root_info.filename
        tree = self.__etree_from_entry(root_info)
        namespaces = {'opf': EPub.Namespace.OPF, 'dc': EPub.Namespace.DUBLIN_CORE}

        res = tree.xpath('/opf:package/opf:metadata/dc:title', namespaces=namespaces)
        if len(res) > 0:
            self.__set_title__(res[0].text)

        res = tree.xpath('/opf:package/opf:metadata/dc:date[@event="modification"]', namespaces=namespaces)
        if len(res) == 0:
            res = tree.xpath('/opf:package/opf:metadata/dc:date', namespaces=namespaces)
        if len(res) > 0:
            self.__set_docdate__(res[0].text)

        res = tree.xpath('/opf:package/opf:metadata/dc:creator[@role="aut"]', namespaces=namespaces)
        if len(res) == 0:
            res = tree.xpath('/opf:package/opf:metadata/dc:creator', namespaces=namespaces)
        for node in res:
            self.__add_author__(node.text)

        res = tree.xpath('/opf:package/opf:metadata/dc:language', namespaces=namespaces)
        if len(res) > 0 and res[0].text:
            self.language_code = res[0].text.strip()

        res = tree.xpath('/opf:package/opf:metadata/dc:subject', namespaces=namespaces)
        for node in res:
            self.__add_tag__(node.text)

        res = tree.xpath('/opf:package/opf:metadata/opf:meta[@name="calibre:series"]', namespaces=namespaces)
        if len(res) > 0:
            series = BookFile.__normalise_string__(res[0].get('content'))
            if series:
                res = tree.xpath('/opf:package/opf:metadata/opf:meta[@name="calibre:series_index"]', namespaces=namespaces)
                index = BookFile.__normalise_string__(res[0].get('content')) if len(res) > 0 else None
                self.series_info = {
                    'title': series,
                    'index': index or None
                }

        res = tree.xpath('/opf:package/opf:metadata/dc:description', namespaces=namespaces)
        if len(res) > 0 and res[0].text:
            self.description = res[0].text.strip()

        prefix = os.path.dirname(root_info.filename)
        if prefix:
            prefix += '/'
        self.cover_fileinfos = self.__find_cover(tree, prefix)

    def __find_cover(self, tree, prefix):
        namespaces = {'opf': EPub.Namespace.OPF, 'dc': EPub.Namespace.DUBLIN_CORE}

        def xpath(query):
            return tree.xpath(query, namespaces=namespaces)[0]

        def item_for_href(ref):
            return xpath('/opf:package/opf:manifest/opf:item[@href="%s"]' % ref)

        def image_infos(node):
            path = os.path.normpath(prefix + node.get('href')).replace('\\','/')
            try:
                fileinfo = self.__zip_file.getinfo(path)
            except Exception:
                fileinfo = self.__zip_file.getinfo(urllib.unquote(path))
            mime = node.get('media-type')
            info = {
                'filename': fileinfo.filename,
                'mime': mime
            }
            if mime.startswith('image/'):
                return [info]
            elif mime == 'application/xhtml+xml':
                xhtml = self.__etree_from_entry(fileinfo)
                xhtml_prefix = os.path.dirname(fileinfo.filename) + '/'
                img = xhtml.xpath('//xhtml:img[@src]', namespaces={'xhtml': EPub.Namespace.XHTML})[0]
                return [info,
                    {
                        'filename': os.path.normpath(xhtml_prefix + img.get('src')),
                        # TODO: detect mimetype
                        'mime': 'image/auto'
                    }
                ]
            else:
                raise Exception('unknown mimetype %s' % mime)

        try:
            node = xpath('/opf:package/opf:manifest/opf:item[@properties="cover-image"]')
            return image_infos(node)
        except Exception:
            pass

        try:
            node = xpath('/opf:package/opf:metadata/opf:meta[@name="cover"]')
            return image_infos(xpath('/opf:package/opf:manifest/opf:item[@id="%s"]' % node.get('content')))
        except Exception:
            pass

        try:
            node = xpath('/opf:package/opf:metadata/meta[@name="cover"]')
            return image_infos(xpath('/opf:package/opf:manifest/opf:item[@id="%s"]' % node.get('content')))
        except Exception:
            pass

        try:
            node = xpath('/package/metadata/meta[@name="cover"]')
            return image_infos(xpath('/package/manifest/item[@id="%s"]' % node.get('content')))
        except Exception:
            pass

        try:
            node = xpath('/opf:package/opf:guide/opf:reference[@type="other.ms-coverimage-standard"][@title="Cover"]')
            return image_infos(item_for_href(node.get('href')))
        except Exception:
            pass

        try:
            node = xpath('/opf:package/opf:guide/opf:reference[@type="other.ms-coverimage-standard"]')
            return image_infos(item_for_href(node.get('href')))
        except Exception:
            pass

        try:
            node = xpath('/opf:package/opf:manifest/opf:item[@id="cover"]')
            return image_infos(node)
        except Exception:
            pass

        return []

    def __get_root_info(self):
        try:
            container_info = self.__zip_file.getinfo(EPub.Entry.CONTAINER)
        except Exception:
            container_info = None
        if container_info:
            tree = self.__etree_from_entry(container_info)
            root_file = None
            namespaces = {'cont': EPub.Namespace.CONTAINER}
            res = tree.xpath('/cont:container/cont:rootfiles/cont:rootfile', namespaces=namespaces)
            if len(res) == 1 and res[0].get('media-type') == 'application/oebps-package+xml':
                root_file = res[0].get('full-path')
            if root_file:
                return self.__zip_file.getinfo(root_file)
        else:
            opf_infos = [i for i in self.__zip_file.infolist() if i.filename.endswith('.opf')]
            if len(opf_infos) > 1:
                raise EPub.StructureException('several OPF files in the archive')
            elif len(opf_infos) == 1:
                return opf_infos[0]

        raise EPub.StructureException('OPF entry not found')

    def __contains_entry(self, name):
        try:
            self.__zip_file.getinfo(name)
            return True
        except KeyError:
            return False

    def extract_cover_internal(self, working_dir):
        if len(self.cover_fileinfos) == 0:
            return (None, False)
        name = self.cover_fileinfos[-1]['filename']
        self.__zip_file.extract(name, path=working_dir)
        split = [part for part in name.split('/') if part]
        if len(split) > 1:
            shutil.move(os.path.join(working_dir, name), os.path.join(working_dir, split[-1]))
            shutil.rmtree(os.path.join(working_dir, split[0]))
        return (split[-1] if len(split) > 0 else None, False)

    def extract_cover_memory(self):
        if len(self.cover_fileinfos) == 0:
            return None
        name = self.cover_fileinfos[-1]['filename']
        content = self.__zip_file.open(name).read()
        return content
