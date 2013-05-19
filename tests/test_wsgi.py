# -*- coding: utf-8 -*-
from cStringIO import StringIO
import os.path
import unittest

import fiole
from ._common import (ENVIRON, handle_single_request,
                      FORM_DATA_CONTENT_TYPE, FORM_DATA_1, FORM_DATA_2)


class FioleTestCase(unittest.TestCase):
    _cookie_secret = fiole.SECRET_KEY

    def setUp(self):
        fiole.Fiole.push()
        fiole.SECRET_KEY = self._cookie_secret

    def tearDown(self):
        fiole.Fiole.pop()
        fiole.SECRET_KEY = self._cookie_secret

    def test_simple(self):
        @fiole.get('/')
        def index(request):
            return 'Hello World!'
        rv = handle_single_request('GET /')
        self.assertEqual(rv['status'], '200 OK')
        self.assertEqual(rv['data'], ['Hello World!'])
        self.assertEqual(rv, {
            'status': '200 OK',
            'headers': [('Content-Type', 'text/html; charset=utf-8'),
                        ('Content-Length', '12')],
            'data': ['Hello World!'],
            'errors': '',
        })

    def test_request_dispatching(self):
        @fiole.get('/')
        def index(request):
            return request.method

        @fiole.get('/more')
        @fiole.post('/more')
        def more(request):
            return request.method

        rv = handle_single_request('GET /')
        self.assertEqual(rv['status'], '200 OK')
        self.assertEqual(rv['data'], ['GET'])

        rv = handle_single_request('POST /')
        self.assertEqual(rv['status'], '405 Method Not Allowed')

        rv = handle_single_request('HEAD /')
        self.assertEqual(rv['status'], '200 OK')
        self.assertFalse(rv['data'])

        rv = handle_single_request('POST /more')
        self.assertEqual(rv['data'], ['POST'])

        rv = handle_single_request('GET /more')
        self.assertEqual(rv['data'], ['GET'])

        rv = handle_single_request('DELETE /more')
        self.assertEqual(rv['status'], '405 Method Not Allowed')

    def test_request_route_placeholder(self):
        @fiole.route(u'/<_mot_>/à/<v_42>')
        def route1(request, _mot_, v_42):
            return u'%s à %s' % (_mot_, v_42)

        rv = handle_single_request(u'GET /table/à/manger')
        self.assertEqual(rv['status'], '200 OK')
        self.assertEqual(rv['data'], [u'table à manger'.encode('utf-8')])

    def test_request_route_regex(self):
        @fiole.route(u'/(?P<a>\d+)/plus/(?P<b>\d+)')
        def addition(request, a, b):
            (a, b) = int(a), int(b)
            return '%d + %d = %d' % (a, b, a + b)

        rv = handle_single_request(u'GET /25/plus/17/')
        self.assertEqual(rv['status'], '200 OK')
        self.assertEqual(rv['data'], ['25 + 17 = 42'])

        rv = handle_single_request(u'GET /navet/plus/tomate/')
        self.assertEqual(rv['status'], '404 Not Found')

    def test_error_handling(self):
        @fiole.errorhandler(404)
        def not_found(exc):
            return 'not found'

        @fiole.errorhandler(500)
        def internal_server_error(exc):
            return 'internal server error'

        @fiole.get('/')
        def index(request):
            raise fiole.NotFound('Lost')

        @fiole.get('/error')
        def error(request):
            1 // 0

        rv = handle_single_request('GET /')
        self.assertEqual(rv['status'], '404 Not Found')
        self.assertEqual(rv['data'], ['not found'])
        self.assertFalse(rv['errors'])
        rv = handle_single_request('GET /error')
        self.assertEqual(rv['status'], '500 Internal Server Error')
        self.assertEqual(rv['data'], ['internal server error'])
        self.assertIn('ZeroDivisionError', rv['errors'])

    def test_user_error_handling(self):
        class MyException(Exception):
            pass

        @fiole.errorhandler(500)
        def system_error(exc):
            if isinstance(exc, MyException):
                return '42'
            return 'internal server error'

        @fiole.get('/')
        def index(request):
            raise MyException()
        rv = handle_single_request('GET /')
        self.assertEqual(rv['status'], '500 Internal Server Error')
        self.assertEqual(rv['data'], ['42'])
        self.assertIn('MyException', rv['errors'])

    def test_response(self):

        @fiole.get('/unicode')
        def from_unicode(request):
            return u'Hällo Wörld'

        @fiole.get('/string')
        def from_string(request):
            return u'Hällo Wörld'.encode('utf-8')

        @fiole.get('/args')
        def from_response(request):
            return fiole.Response('Meh', headers=[('X-Foo', 'Testing')],
                                  status=400, content_type='text/plain')

        rv = handle_single_request('GET /unicode')
        self.assertEqual(rv['data'], [u'Hällo Wörld'.encode('utf-8')])
        rv = handle_single_request('GET /string')
        self.assertEqual(rv['data'], [u'Hällo Wörld'.encode('utf-8')])
        rv = handle_single_request('GET /args')
        self.assertEqual(rv, {
            'status': '400 Bad Request',
            'headers': [('X-Foo', 'Testing'),
                        ('Content-Type', 'text/plain; charset=utf-8'),
                        ('Content-Length', '3')],
            'data': ['Meh'],
            'errors': '',
        })

        rv = fiole.Response('')
        html_utf8 = 'text/html; charset=utf-8'
        self.assertEqual(rv.status, 200)
        self.assertEqual(rv.output, '')
        self.assertEqual(rv.headers['Content-Type'], html_utf8)

        rv = fiole.Response('Awesome')
        self.assertEqual(rv.status, 200)
        self.assertEqual(rv.output, 'Awesome')
        self.assertEqual(rv.headers['Content-Type'], html_utf8)

        rv = fiole.Response('W00t', status=404)
        self.assertEqual(rv.status, 404)
        self.assertEqual(rv.output, 'W00t')
        self.assertEqual(rv.headers['Content-Type'], html_utf8)

    def test_none_response(self):

        @fiole.get('/')
        def index(request):
            return

        rv = handle_single_request('GET /')
        self.assertEqual(rv['status'], '200 OK')
        self.assertEqual(rv['data'], [''])

    def test_redirect(self):

        @fiole.get('/')
        def index(request):
            raise fiole.Redirect('/far')

        rv = handle_single_request('GET /')
        self.assertEqual(rv['status'], '302 Found')
        self.assertEqual(rv['data'], [''])
        self.assertIn(('Location', '/far'), rv['headers'])

    def test_redirect_error_handler(self):

        @fiole.errorhandler(500)
        def handle_500_redirect(request):
            raise fiole.Redirect('/far')

        @fiole.get('/')
        def index(request):
            1 // 0

        rv = handle_single_request('GET /')
        self.assertEqual(rv['status'], '302 Found')
        self.assertEqual(rv['data'], [''])
        self.assertIn(('Location', '/far'), rv['headers'])
        # Is it correct?
        self.assertIn('ZeroDivisionError', rv['errors'])

    def test_form_data_1(self):
        environ = dict(ENVIRON)
        environ.update({
            'REQUEST_METHOD': 'POST',
            'CONTENT_TYPE': FORM_DATA_CONTENT_TYPE,
            'CONTENT_LENGTH': len(FORM_DATA_1),
            'wsgi.input': StringIO(FORM_DATA_1),
        })
        request = fiole.Request(environ)
        self.assertFalse(request.GET)
        self.assertFalse(request.cookies)
        self.assertEqual(sorted(request.POST), ['files', 'submit-name'])
        self.assertEqual(request.POST['submit-name'], 'Larry')
        self.assertEqual(request.POST['files'].filename, 'file1.txt')
        self.assertEqual(request.POST['files'].file.read(),
                         '... contents of file1.txt ...')
        self.assertEqual(request.POST['files'].value,
                         '... contents of file1.txt ...')
        self.assertEqual(request.POST['files'].type, 'text/plain')
        self.assertEqual(request.POST['files'].disposition, 'form-data')

    def test_form_data_2(self):
        environ = dict(ENVIRON)
        environ.update({
            'REQUEST_METHOD': 'POST',
            'CONTENT_LENGTH': len(FORM_DATA_2),
            'CONTENT_TYPE': FORM_DATA_CONTENT_TYPE,
            'wsgi.input': StringIO(FORM_DATA_2),
        })
        request = fiole.Request(environ)
        self.assertFalse(request.GET)
        self.assertFalse(request.cookies)
        self.assertEqual(sorted(request.POST), ['files', 'submit-name'])
        self.assertEqual(request.POST['submit-name'], 'Larry')
        files = dict([(f.filename, f) for f in request.POST['files']])
        self.assertEqual(sorted(files), ['file1.txt', 'file2.gif'])

        self.assertEqual(files['file1.txt'].value,
                         '... contents of file1.txt ...')
        self.assertEqual(files['file1.txt'].type, 'text/plain')
        self.assertEqual(files['file1.txt'].disposition, 'file')

        self.assertEqual(files['file2.gif'].value,
                         '...contents of file2.gif...')
        self.assertEqual(files['file2.gif'].type, 'image/gif')
        self.assertEqual(files['file2.gif'].disposition, 'file')

    def test_upload(self):

        @fiole.post('/upload')
        def post_upload(request):
            return '42'

        environ = {
            'CONTENT_TYPE': FORM_DATA_CONTENT_TYPE,
            'CONTENT_LENGTH': len(FORM_DATA_1),
            'wsgi.input': StringIO(FORM_DATA_1),
        }
        rv = handle_single_request('GET /upload', **environ)
        self.assertEqual(rv['status'], '405 Method Not Allowed')

        rv = handle_single_request('POST /nothing-here', **environ)
        self.assertEqual(rv['status'], '404 Not Found')

        rv = handle_single_request('POST /upload', **environ)
        self.assertEqual(rv['status'], '200 OK')
        self.assertEqual(rv['data'], ['42'])
        self.assertEqual(rv['headers'],
                         [('Content-Type', 'text/html; charset=utf-8'),
                          ('Content-Length', '2')])
        self.assertFalse(rv['errors'])

    def test_cookie(self):

        @fiole.get('/send')
        def send_cookie(request):
            response = fiole.Response('+ empty +')
            response.set_cookie('nickname', 'gaston')
            response.set_cookie('session', 'czpwoe83q8ape2ji23jxnm')
            return response

        # Send cookie
        rv = handle_single_request('GET /send')
        self.assertEqual(rv['status'], '200 OK')
        self.assertEqual(rv['headers'], [
            ('Content-Type', 'text/html; charset=utf-8'),
            ('Content-Length', '9'),
            ('Set-Cookie', 'session=czpwoe83q8ape2ji23jxnm; Path=/'),
            ('Set-Cookie', 'nickname=gaston; Path=/')])
        self.assertFalse(rv['errors'])

    def test_secure_cookie(self):
        fiole.SECRET_KEY = 's e c r e t'

        @fiole.get('/receive')
        def receive_cookies(request):
            cookies = [name + '=' + request.get_cookie(name)
                       for name in request.cookies]
            secure_cookie = request.get_secure_cookie('foo')
            content = cookies + [secure_cookie]
            response = fiole.Response(content, content_type='text/plain',
                                      wrapped=True)
            return response

        @fiole.get('/send_secure')
        def send_secure_cookie(request):
            response = fiole.Response('+ empty +')
            response.set_secure_cookie('foo', 'bar')
            return response

        @fiole.get('/clear')
        def clear_cookies(request):
            response = fiole.Response('+ empty +')
            for name in request.cookies:
                response.clear_cookie(name)
            return response

        # Send secure cookie
        rv = handle_single_request('GET /send_secure')
        self.assertEqual(rv['status'], '200 OK')
        self.assertEqual([h for (h, v) in rv['headers']],
                         ['Content-Type', 'Content-Length', 'Set-Cookie'])
        cookie, expires, path = rv['headers'][2][1].split('; ')
        self.assertEqual(cookie[:9], 'foo=YmFy|')
        self.assertEqual(expires[:8], 'expires=')
        self.assertEqual(path, 'Path=/')

        # Receive cookies
        rv = handle_single_request('GET /receive', HTTP_COOKIE=cookie)
        self.assertEqual(rv['status'], '200 OK')
        self.assertEqual([h for (h, v) in rv['headers']], ['Content-Type'])
        (raw_cookie, secure_cookie) = rv['data']
        self.assertEqual(raw_cookie, cookie)
        self.assertEqual(secure_cookie, 'bar')

        # Clear cookies
        cookie = 'nickname=gaston; ' + cookie
        rv = handle_single_request('GET /clear', HTTP_COOKIE=cookie)
        self.assertEqual(rv['status'], '200 OK')
        self.assertEqual([h for (h, v) in rv['headers']],
                         ['Content-Type', 'Content-Length',
                          'Set-Cookie', 'Set-Cookie'])
        cookie1, expires1, path1 = rv['headers'][2][1].split('; ')
        cookie2, expires2, path2 = rv['headers'][3][1].split('; ')
        self.assertEqual(sorted([cookie1, cookie2]), ['foo=', 'nickname='])
        self.assertEqual(expires1[:8], 'expires=')
        self.assertEqual(expires2[:8], 'expires=')
        self.assertEqual(path1, 'Path=/')
        self.assertEqual(path2, 'Path=/')

    def test_send_file(self):
        fname = os.path.splitext(__file__)[0] + '.py'
        rootdir, fname = os.path.split(fname)

        @fiole.get('/img/logo.png')
        def img_logo(request):
            return fiole.send_file(request, fname, root=rootdir)

        rv = handle_single_request('GET /img/logo.png')
        self.assertEqual(rv['status'], '200 OK')
        self.assertFalse(rv['errors'])
        data = ''.join([chunk for chunk in rv['data']])
        with open(os.path.join(rootdir, fname)) as f:
            self.assertEqual(data, f.read())
