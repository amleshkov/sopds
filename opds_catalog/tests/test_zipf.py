# -*- coding: utf-8 -*-

import io
import zipfile as stdlib_zipfile

from django.test import TestCase

from constance import config
from opds_catalog import zipf


def make_cp866_zip():
    placeholder = b'ABCDEFGHIJ'
    cp866_name = 'Пушкин.fb2'.encode('cp866')
    assert len(placeholder) == len(cp866_name)

    buf = io.BytesIO()
    with stdlib_zipfile.ZipFile(buf, 'w', stdlib_zipfile.ZIP_DEFLATED) as zf:
        info = stdlib_zipfile.ZipInfo(placeholder.decode('ascii'), (2026, 1, 1, 0, 0, 0))
        zf.writestr(info, b'book content')

    raw = buf.getvalue()
    count = raw.count(placeholder)
    assert count >= 2
    return io.BytesIO(raw.replace(placeholder, cp866_name))


class zipfTestCase(TestCase):

    def test_cp866_zip_names_decoded(self):
        config.SOPDS_ZIPCODEPAGE = 'cp866'
        z = zipf.ZipFile(make_cp866_zip(), 'r')
        try:
            self.assertEqual(z.namelist(), ['Пушкин.fb2'])
            self.assertEqual(z.read('Пушкин.fb2'), b'book content')
        finally:
            z.close()

    def test_utf8_zip_names_untouched(self):
        config.SOPDS_ZIPCODEPAGE = 'cp866'
        buf = io.BytesIO()
        with stdlib_zipfile.ZipFile(buf, 'w') as zf:
            zf.writestr('Тургенев.fb2', b'data')
        z = zipf.ZipFile(io.BytesIO(buf.getvalue()), 'r')
        try:
            self.assertEqual(z.namelist(), ['Тургенев.fb2'])
        finally:
            z.close()

    def test_write_zip(self):
        config.SOPDS_ZIPCODEPAGE = 'cp866'
        buf = io.BytesIO()
        z = zipf.ZipFile(buf, 'w', zipf.ZIP_DEFLATED)
        try:
            z.writestr(' Pushkin.fb2', b'data')
        finally:
            z.close()
        with stdlib_zipfile.ZipFile(io.BytesIO(buf.getvalue())) as zf:
            self.assertEqual(zf.namelist(), [' Pushkin.fb2'])
