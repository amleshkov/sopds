# -*- coding: utf-8 -*-
from django.test import TestCase

from book_tools.pymobi import compression, util


class palmdocTestCase(TestCase):

    def test_unpack_literal_characters(self):
        result = compression.Palmdoc().unpack('ABC\x00')
        self.assertEqual(result, 'ABC\x00')

    def test_unpack_space_and_char(self):
        result = compression.Palmdoc().unpack('\u00c1\x00')
        self.assertEqual(result, ' A\x00')

    def test_unpack3_bytes_mode(self):
        result = compression.Palmdoc().unpack3(bytes([0x41, 0x42, 0x00]))
        self.assertEqual(result, b'AB\x00')

    def test_uncompression_passthrough(self):
        passthrough = compression.Uncompression()
        self.assertEqual(passthrough.unpack(b'xyz'), b'xyz')
        self.assertEqual(passthrough.pack(b'xyz'), b'xyz')

    def test_palmdoc_pack_not_implemented(self):
        with self.assertRaises(ValueError):
            compression.Palmdoc().pack(b'x')


class varintTestCase(TestCase):

    def test_varint_roundtrip(self):
        for value in (0, 1, 5, 127):
            encoded = util.encodeVarint(value)
            self.assertEqual(util.decodeVarint(encoded), value)

    def test_toStr_toByte(self):
        self.assertEqual(util.toStr(b'abc'), 'abc')
        self.assertEqual(util.toByte('abc'), b'abc')
