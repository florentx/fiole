# -*- coding: utf-8 -*-
import unittest

import fiole


class AcceptTestCase(unittest.TestCase):

    def test_parse_accept_badq(self):
        self.assertEqual(list(fiole.Accept.parse("value1; q=0.1.2")),
                         [('value1', 1)])

    def test_init_accept_content_type(self):
        accept = fiole.Accept('Accept', 'text/html')
        self.assertEqual(accept._parsed, [('text/html', 1)])

    def test_init_accept_accept_charset(self):
        # http://www.w3.org/Protocols/rfc2616/rfc2616-sec14.html#sec14.2
        accept = fiole.Accept('Accept-Charset',
                              'iso-8859-5, unicode-1-1;q=0.8')
        # Not RFC compliant, but Accept-Charset is not worth it.
        # https://code.google.com/p/chromium/issues/detail?id=112804
        self.assertEqual(accept._parsed,
                         [('iso-8859-5', 1), ('unicode-1-1', 0.8)])
        # (the RFC specifies default q=1 for ISO-8859-1)

    def test_init_accept_accept_charset_mixedcase(self):
        """HTTP character sets are identified by case-insensitive tokens."""
        accept = fiole.Accept('Accept-Charset',
                              'ISO-8859-5, UNICODE-1-1;q=0.8')
        self.assertEqual(accept._parsed,
                         [('iso-8859-5', 1), ('unicode-1-1', 0.8)])

    def test_init_accept_accept_charset_wildcard(self):
        accept = fiole.Accept('Accept-Charset', '*')
        self.assertEqual(accept._parsed, [('*', 1)])

    def test_init_accept_accept_language(self):
        accept = fiole.Accept('Accept-Language', 'da, en-gb;q=0.8, en;q=0.7')
        self.assertEqual(accept._parsed,
                         [('da', 1), ('en-gb', 0.8), ('en', 0.7)])

    def test_init_accept_invalid_value(self):
        accept = fiole.Accept('Accept-Language', 'da, q, en-gb;q=0.8')
        self.assertEqual(accept._parsed, [('da', 1), ('en-gb', 0.8)])

        accept = fiole.Accept('Accept-Language', 'da, en-gb;q=foo')
        self.assertEqual(accept._parsed, [('da', 1), ('en-gb', 1)])

    def test_zero_quality(self):
        accept = fiole.Accept('Accept', 'bar, *;q=0')
        self.assertIsNone(accept.best_match(['foo']))
        self.assertNotIn('foo', fiole.Accept('Accept', '*;q=0'))

    def test_contains(self):
        accept = fiole.Accept('Accept', 'text/html')
        self.assertIn('text/html', accept)

    def test_contains_not(self):
        accept = fiole.Accept('Accept', 'text/html')
        self.assertNotIn('foo/bar', accept)

    def test_quality(self):
        accept = fiole.Accept('Accept', 'text/html')
        self.assertEqual(accept.quality('text/html'), 1)
        accept = fiole.Accept('Accept', 'text/html;q=0.5')
        self.assertEqual(accept.quality('text/html'), 0.5)

    def test_quality_not_found(self):
        accept = fiole.Accept('Accept', 'text/html')
        self.assertIsNone(accept.quality('foo/bar'))

    def test_best_match(self):
        accept = fiole.Accept('Accept', 'text/html, foo/bar')
        self.assertEqual(accept.best_match(['text/html', 'foo/bar']),
                         'text/html')
        self.assertEqual(accept.best_match(['foo/bar', 'text/html']),
                         'foo/bar')
        self.assertEqual(accept.best_match([('foo/bar', 0.5), 'text/html']),
                         'text/html')
        self.assertEqual(accept.best_match(
            [('foo/bar', 0.5), ('text/html', 0.4)]), 'foo/bar')
        self.assertRaises(AssertionError, accept.best_match, ['text/*'])
        self.assertRaises(AssertionError, accept.best_match, ['*/*'])

    def test_best_match_with_one_lower_q(self):
        accept = fiole.Accept('Accept', 'text/html, foo/bar;q=0.5')
        self.assertEqual(accept.best_match(['text/html', 'foo/bar']),
                         'text/html')

        accept = fiole.Accept('Accept', 'text/html;q=0.5, foo/bar')
        self.assertEqual(accept.best_match(['text/html', 'foo/bar']),
                         'foo/bar')

    def test_best_match_with_complex_q(self):
        accept = fiole.Accept('Accept',
                              'text/html, foo/bar;q=0.55, baz/gort;q=0.59')
        self.assertEqual(accept.best_match(['text/html', 'foo/bar']),
                         'text/html')

        accept = fiole.Accept('Accept', 'text/html;q=0.5, '
                              'foo/bar;q=0.586, baz/gort;q=0.5966')
        self.assertEqual(accept.best_match(['text/html', 'baz/gort']),
                         'baz/gort')

    def test_accept_match(self):
        for mask in ['*', 'text/html', 'TEXT/HTML']:
            self.assertIn('text/html', fiole.Accept('Accept', mask))
        self.assertNotIn('text/html', fiole.Accept('Accept', 'foo/bar'))

    def test_accept_match_lang(self):
        for mask, lang in [('*', 'da'),
                           ('da', 'DA'),
                           ('en', 'en-gb'),
                           ('en-gb', 'en-gb'),
                           ('en-gb', 'en'),
                           ('en-gb', 'en_GB')]:
            self.assertIn(lang, fiole.Accept('Accept-Language', mask),
                          msg='%r not in AcceptLanguage: %r' % (lang, mask))
        for mask, lang in [('en-gb', 'en-us'),
                           ('en-gb', 'fr-fr'),
                           ('en-gb', 'fr'),
                           ('en', 'fr-fr')]:
            self.assertNotIn(lang, fiole.Accept('Accept-Language', mask))

    # Missing Accept tests

    def test_nil(self):
        nilaccept = fiole.Accept('Accept', None)
        self.assertFalse(nilaccept)
        self.assertIsNone(nilaccept.quality('dummy'))
        self.assertIn('anything', nilaccept)

    def test_nil_best_match(self):
        nilaccept = fiole.Accept('Accept', None)
        nil_best_match = nilaccept.best_match
        self.assertEqual(nil_best_match(['foo', 'bar']), 'foo')
        self.assertEqual(nil_best_match([('foo', 1), ('bar', 0.5)]), 'foo')
        self.assertEqual(nil_best_match([('foo', 0.5), ('bar', 1)]), 'bar')
        self.assertEqual(nil_best_match([('foo', 0.5), 'bar']), 'bar')
        self.assertEqual(nil_best_match([('foo', 0.5), 'bar'],
                                        default_match=True), 'bar')
        self.assertEqual(nil_best_match([('foo', 0.5), 'bar'],
                                        default_match=False), 'bar')
        self.assertEqual(nil_best_match([], default_match='fallback'),
                         'fallback')

    # Missing Accept-Encoding test
    def test_accept_encoding_contains(self):
        nilaccept = fiole.Accept('Accept-Encoding', None)
        self.assertNotIn('text/plain', nilaccept)

    # MIMEAccept tests

    def test_mime_init(self):
        mimeaccept = fiole.Accept('Accept', 'image/jpg')
        self.assertIn('image/jpg', mimeaccept)
        self.assertNotIn('image/png', mimeaccept)
        self.assertEqual(mimeaccept._parsed, [('image/jpg', 1)])

        mimeaccept = fiole.Accept('Accept', 'image/png, image/jpg;q=0.5')
        self.assertIn('image/jpg', mimeaccept)
        self.assertIn('image/png', mimeaccept)
        self.assertEqual(mimeaccept._parsed,
                         [('image/png', 1), ('image/jpg', 0.5)])

        mimeaccept = fiole.Accept('Accept', '*/*')
        self.assertIn('image/jpg', mimeaccept)
        self.assertIn('image/png', mimeaccept)
        self.assertEqual(mimeaccept._parsed, [('*/*', 1)])

        mimeaccept = fiole.Accept('Accept', 'image, image/jpg;q=0.5')
        self.assertIn('image/jpg', mimeaccept)
        self.assertNotIn('image/png', mimeaccept)
        mimeaccept = fiole.Accept('Accept', '*/png')
        self.assertNotIn('image/png', mimeaccept)
        mimeaccept = fiole.Accept('Accept', 'image/pn*')
        self.assertNotIn('image/png', mimeaccept)
        mimeaccept = fiole.Accept('Accept', 'imag*/png')
        self.assertNotIn('image/png', mimeaccept)
        mimeaccept = fiole.Accept('Accept', 'image/*')
        self.assertIn('image/png', mimeaccept)
        self.assertEqual(mimeaccept._parsed, [('image/*', 1)])
        self.assertRaises(AssertionError, mimeaccept.__contains__, '*/*')

    def test_match(self):
        mimeaccept = fiole.Accept('Accept', 'image/jpg')
        self.assertTrue(mimeaccept._match('image/jpg', 'image/jpg'))
        self.assertTrue(mimeaccept._match('image/*', 'image/jpg'))
        self.assertTrue(mimeaccept._match('*/*', 'image/jpg'))

        self.assertFalse(mimeaccept._match('text/html', 'image/jpg'))

    def test_accept_json(self):
        mimeaccept = fiole.Accept('Accept', 'text/html, *; q=0.2, */*; q=0.2')
        self.assertIn('application/json', mimeaccept)
        self.assertEqual(mimeaccept.best_match(['application/json']),
                         'application/json')

    def test_match_mixedcase(self):
        mimeaccept = fiole.Accept('Accept', 'image/jpg; q=0.2, '
                                  'Image/pNg; Q=0.4, image/*; q=0.05')
        self.assertEqual(mimeaccept.best_match(['Image/JpG']), 'Image/JpG')
        self.assertEqual(mimeaccept.best_match(['image/Tiff']), 'image/Tiff')
        self.assertEqual(mimeaccept.best_match(
            ['image/Tiff', 'image/PnG', 'image/jpg']), 'image/PnG')

    def test_nomatch_uppercase_q(self):
        """The relative-quality-factor "q" parameter should be lowercase."""
        mimeaccept = fiole.Accept('Accept', 'image/jpg; q=0.4, '
                                  'Image/pNg; Q=0.2, image/*; q=0.05')
        self.assertEqual(mimeaccept._parsed, [
            ('image/jpg', 0.4), ('image/png', 1.0), ('image/*', 0.05)])
