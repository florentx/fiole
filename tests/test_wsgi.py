# -*- coding: utf-8 -*-
import os.path
import unittest
try:
    from cStringIO import StringIO as BytesIO
except ImportError:
    from io import BytesIO

import fiole
from ._common import (PY3, ENVIRON, handle_single_request,
                      FORM_DATA_CONTENT_TYPE, FORM_DATA_1, FORM_DATA_2)
u = (lambda s: s) if PY3 else (lambda s: s.decode('utf-8'))
b = (lambda s: s.encode('utf-8')) if PY3 else (lambda s: s)


class FioleTestCase(unittest.TestCase):
    maxDiff = 0x800

    def setUp(self):
        fiole.Fiole.push()

    def tearDown(self):
        fiole.Fiole.pop()

    def assertNoError(self, response):
        self.assertFalse(response['errors'], msg=response['errors'])
        self.assertEqual(response['status'], '200 OK')

    def install_dummy_hook(self):
        app_hooks = fiole.get_app().hooks

        captured = []

        @app_hooks.append
        def dummy_hook(request):
            request.dummy = body = captured
            body.append('acquire resource')
            try:
                body.append('pre-process request')
                response = yield
                body.append('post-process response')
                body.append('response = %s' % response.output)
                response.output = '\n'.join(body)
                yield response
                body.append('not executed')
            finally:
                # release resource
                body.append('release resource')
                del body, request.dummy

        return captured

    def test_simple(self):
        @fiole.get('/')
        def index(request):
            return 'Hello World!'
        rv = handle_single_request('GET /')
        self.assertNoError(rv)
        self.assertEqual(rv['data'], [b('Hello World!')])
        self.assertEqual(rv, {
            'status': '200 OK',
            'headers': [('Content-Type', 'text/html; charset=utf-8'),
                        ('Content-Length', '12')],
            'data': [b('Hello World!')],
            'errors': '',
        })

    def test_head(self):
        @fiole.get('/')
        def index(request):
            return 'Hello World!'
        rv = handle_single_request('HEAD /')
        self.assertNoError(rv)
        self.assertEqual(rv, {
            'status': '200 OK',
            'headers': [('Content-Type', 'text/html; charset=utf-8'),
                        ('Content-Length', '12')],
            'data': [],
            'errors': '',
        })

    def test_request(self):
        @fiole.get('/foo/bar')
        def foobar(request):
            host_url = 'https://fakehost.invalid'
            hdrs_dict = {'Content-Type': 'text/plain',
                         'Content-Length': '',
                         'Cookie': ''}
            self.assertEqual(request.method, 'GET')
            self.assertEqual(request.path, '/foo/bar/')
            self.assertEqual(request.query, 'k=baz')
            self.assertEqual(request.host_url, host_url)
            self.assertEqual(request.get_url(), '/foo/bar/')
            self.assertEqual(request.get_url(full=True), host_url+'/foo/bar/')
            self.assertEqual(request.get_url('baz.yl/ur', full=True),
                             host_url+'/foo/bar/baz.yl/ur')
            self.assertEqual(request.get_url('az.yl/r/'), '/foo/bar/az.yl/r/')
            self.assertEqual(request.get_url('/baz/yl.ur'), '/baz/yl.ur')
            self.assertEqual(dict(request.headers), hdrs_dict)
            self.assertTrue(request.environ)
            self.assertEqual(list(request.accept), [])
            self.assertEqual(list(request.accept_charset), [])
            self.assertEqual(list(request.accept_encoding), [])
            self.assertEqual(list(request.accept_language), [])
            self.assertEqual(request.GET, {'k': 'baz'})
            self.assertEqual(request.POST, {})
            self.assertEqual(request.PUT, request.POST)
            self.assertEqual(request.body, b(''))
            self.assertEqual(request.content_length, 0)
            self.assertEqual(request.cookies, {})
            return 'all right'
        rv = handle_single_request('GET /foo/bar?k=baz')
        self.assertNoError(rv)
        self.assertEqual(rv, {
            'status': '200 OK',
            'headers': [('Content-Type', 'text/html; charset=utf-8'),
                        ('Content-Length', '9')],
            'data': [b('all right')],
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
        self.assertNoError(rv)
        self.assertEqual(rv['data'], [b('GET')])

        rv = handle_single_request('POST /')
        self.assertEqual(rv['status'], '405 Method Not Allowed')

        rv = handle_single_request('HEAD /')
        self.assertNoError(rv)
        self.assertFalse(rv['data'])

        rv = handle_single_request('POST /more')
        self.assertEqual(rv['data'], [b('POST')])

        rv = handle_single_request('GET /more')
        self.assertEqual(rv['data'], [b('GET')])

        rv = handle_single_request('DELETE /more')
        self.assertEqual(rv['status'], '405 Method Not Allowed')

    def test_request_route_placeholder(self):
        @fiole.route(u('/<_mot_>/à/<v_42>'))
        def route1(request, _mot_, v_42):
            return u('%s à %s') % (_mot_, v_42)

        rv = handle_single_request(u('GET /table/à/manger'))
        self.assertNoError(rv)
        self.assertEqual(rv['data'], [b('table à manger')])

    def test_request_route_regex(self):
        @fiole.route(u('/(?P<a>\d+)/plus/(?P<b>\d+)'))
        def addition(request, a, b):
            (a, b) = int(a), int(b)
            return '%d + %d = %d' % (a, b, a + b)

        rv = handle_single_request(u('GET /25/plus/17/'))
        self.assertNoError(rv)
        self.assertEqual(rv['data'], [b('25 + 17 = 42')])

        rv = handle_single_request(u('GET /navet/plus/tomate/'))
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
        self.assertEqual(rv['data'], [b('not found')])
        self.assertFalse(rv['errors'])
        rv = handle_single_request('GET /error')
        self.assertEqual(rv['status'], '500 Internal Server Error')
        self.assertEqual(rv['data'], [b('internal server error')])
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
        self.assertEqual(rv['data'], [b('42')])
        self.assertIn('MyException', rv['errors'])

    def test_response(self):

        @fiole.get('/unicode')
        def from_unicode(request):
            return u('Hällo Wörld')

        @fiole.get('/string')
        def from_string(request):
            return b('Hällo Wörld')

        @fiole.get('/args')
        def from_response(request):
            return fiole.Response('Meh', headers=[('X-Foo', 'Testing')],
                                  status=400, content_type='text/plain')

        rv = handle_single_request('GET /unicode')
        self.assertEqual(rv['data'], [b('Hällo Wörld')])
        rv = handle_single_request('GET /string')
        self.assertEqual(rv['data'], [b('Hällo Wörld')])
        rv = handle_single_request('GET /args')
        self.assertEqual(rv, {
            'status': '400 Bad Request',
            'headers': [('X-Foo', 'Testing'),
                        ('Content-Type', 'text/plain; charset=utf-8'),
                        ('Content-Length', '3')],
            'data': [b('Meh')],
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
        self.assertNoError(rv)
        self.assertEqual(rv['data'], [])

    def test_redirect(self):

        @fiole.get('/')
        def index(request):
            raise fiole.Redirect('/far')

        rv = handle_single_request('GET /')
        self.assertEqual(rv['status'], '302 Found')
        self.assertEqual(rv['data'], [])
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
        self.assertEqual(rv['data'], [])
        self.assertIn(('Location', '/far'), rv['headers'])
        # Is it correct?
        self.assertIn('ZeroDivisionError', rv['errors'])

    def test_form_data_1(self):
        environ = dict(ENVIRON)
        environ.update({
            'REQUEST_METHOD': 'POST',
            'CONTENT_TYPE': FORM_DATA_CONTENT_TYPE,
            'CONTENT_LENGTH': len(FORM_DATA_1),
            'wsgi.input': BytesIO(FORM_DATA_1),
        })
        request = fiole.Request(environ)
        self.assertFalse(request.GET)
        self.assertFalse(request.cookies)
        self.assertEqual(sorted(request.POST), ['files', 'submit-name'])
        self.assertEqual(request.POST['submit-name'], 'Larry')
        self.assertEqual(request.POST['files'].filename, 'file1.txt')
        self.assertEqual(request.POST['files'].file.read(),
                         b('... contents of file1.txt ...'))
        self.assertEqual(request.POST['files'].value,
                         b('... contents of file1.txt ...'))
        self.assertEqual(request.POST['files'].type, 'text/plain')
        self.assertEqual(request.POST['files'].disposition, 'form-data')

        self.assertFalse(hasattr(request, 'db'))
        self.assertRaises(AttributeError, getattr, request, 'db')

    def test_form_data_2(self):
        environ = dict(ENVIRON)
        environ.update({
            'REQUEST_METHOD': 'POST',
            'CONTENT_LENGTH': len(FORM_DATA_2),
            'CONTENT_TYPE': FORM_DATA_CONTENT_TYPE,
            'wsgi.input': BytesIO(FORM_DATA_2),
        })
        request = fiole.Request(environ)
        self.assertFalse(request.GET)
        self.assertFalse(request.cookies)
        self.assertEqual(sorted(request.POST), ['files', 'submit-name'])
        self.assertEqual(request.POST['submit-name'], 'Larry')
        files = dict([(f.filename, f) for f in request.POST['files']])
        self.assertEqual(sorted(files), ['file1.txt', 'file2.gif'])

        self.assertEqual(files['file1.txt'].value,
                         b('... contents of file1.txt ...'))
        self.assertEqual(files['file1.txt'].type, 'text/plain')
        self.assertEqual(files['file1.txt'].disposition, 'file')

        self.assertEqual(files['file2.gif'].value,
                         b('...contents of file2.gif...'))
        self.assertEqual(files['file2.gif'].type, 'image/gif')
        self.assertEqual(files['file2.gif'].disposition, 'file')

    def test_upload(self):

        @fiole.post('/upload')
        def post_upload(request):
            return '42'

        environ = {
            'CONTENT_TYPE': FORM_DATA_CONTENT_TYPE,
            'CONTENT_LENGTH': len(FORM_DATA_1),
            'wsgi.input': BytesIO(FORM_DATA_1),
        }
        rv = handle_single_request('GET /upload', **environ)
        self.assertEqual(rv['status'], '405 Method Not Allowed')

        rv = handle_single_request('POST /nothing-here', **environ)
        self.assertEqual(rv['status'], '404 Not Found')

        rv = handle_single_request('POST /upload', **environ)
        self.assertNoError(rv)
        self.assertEqual(rv['data'], [b('42')])
        self.assertEqual(rv['headers'],
                         [('Content-Type', 'text/html; charset=utf-8'),
                          ('Content-Length', '2')])
        self.assertFalse(rv['errors'])

    def test_cookie(self):

        @fiole.get('/receive')
        def receive_cookies(request):
            cookies = [request.get_cookie(name)
                       for name in sorted(request.cookies)]
            content = cookies
            response = fiole.Response(content, content_type='text/plain',
                                      wrapped=True)
            return response

        @fiole.get('/send')
        def send_cookie(request):
            response = fiole.Response('+ empty +')
            response.set_cookie('nickname', u('gästõn'))
            response.set_cookie('session', 'czpwoe83q8ape2ji23jxnm')
            return response

        gaston = r'g\344st\365n' if PY3 else r'g\303\244st\303\265n'
        # Send cookie
        rv = handle_single_request('GET /send')
        self.assertNoError(rv)
        self.assertEqual(sorted(rv['headers']), [
            ('Content-Length', '9'),
            ('Content-Type', 'text/html; charset=utf-8'),
            ('Set-Cookie', 'nickname="%s"; Path=/' % gaston),
            ('Set-Cookie', 'session=czpwoe83q8ape2ji23jxnm; Path=/'),
        ])
        cookies = [v.split(';')[0]
                   for (k, v) in rv['headers'] if k == 'Set-Cookie']
        cookie = '; '.join(cookies)

        # Receive cookies
        rv = handle_single_request('GET /receive', HTTP_COOKIE=cookie)
        self.assertNoError(rv)
        self.assertEqual([h for (h, v) in rv['headers']], ['Content-Type'])
        self.assertEqual(rv['data'], ['gästõn', 'czpwoe83q8ape2ji23jxnm'])

    def test_secure_cookie(self):
        fiole.get_app().secret_key = 's e c r e t'

        @fiole.get('/receive')
        def receive_cookies(request):
            cookies = ['%s="%s"' % (name, request.get_cookie(name))
                       for name in request.cookies]
            secure_cookie = request.get_secure_cookie('foo')
            content = cookies + [secure_cookie]
            response = fiole.Response(content, content_type='text/plain',
                                      wrapped=True)
            return response

        @fiole.get('/send_secure')
        def send_secure_cookie(request):
            response = fiole.Response('+ empty +')
            response.set_secure_cookie('foo', u('bär'))
            return response

        @fiole.get('/clear')
        def clear_cookies(request):
            response = fiole.Response('+ empty +')
            for name in request.cookies:
                response.clear_cookie(name)
            return response

        # Send secure cookie
        rv = handle_single_request('GET /send_secure')
        self.assertNoError(rv)
        self.assertEqual([h for (h, v) in rv['headers']],
                         ['Content-Type', 'Content-Length', 'Set-Cookie'])
        cookie, expires, path = rv['headers'][2][1].split('; ')
        cookie_kv = cookie.split('|')[0]
        self.assertEqual(cookie_kv, 'foo="YsOkcg==')
        self.assertEqual(expires[:8], 'expires=')
        self.assertEqual(path, 'Path=/')

        # Receive cookies
        rv = handle_single_request('GET /receive', HTTP_COOKIE=cookie)
        self.assertNoError(rv)
        self.assertEqual([h for (h, v) in rv['headers']], ['Content-Type'])
        (raw_cookie, secure_cookie) = rv['data']
        self.assertEqual(raw_cookie, cookie)
        self.assertEqual(secure_cookie, u('bär'))

        # Clear cookies
        cookie = 'nickname=gaston; ' + cookie
        rv = handle_single_request('GET /clear', HTTP_COOKIE=cookie)
        self.assertNoError(rv)
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
        fname = fiole.__file__
        rootdir, fname = os.path.split(fname)
        self.assertTrue(os.path.isabs(fiole.__file__))

        @fiole.get('/img/logo.png')
        def img_logo(request):
            return fiole.send_file(request, fname, root=rootdir)

        rv = handle_single_request('GET /img/logo.png')
        try:
            self.assertNoError(rv)
            data = b('').join([chunk for chunk in rv['data']])
            with open(os.path.join(rootdir, fname), 'rb') as f:
                self.assertEqual(data, f.read())
        finally:
            rv['data'].close()

    def test_send_file_not_modified(self):
        fname = fiole.__file__
        mtime = os.path.getmtime(fname)
        rootdir, fname = os.path.split(fname)

        @fiole.get('/img/logo.png')
        def img_logo(request):
            return fiole.send_file(request, fname, root=rootdir)

        past_date = fiole.format_timestamp(mtime - 42)
        next_date = fiole.format_timestamp(mtime + 42)

        rv = handle_single_request('GET /img/logo.png',
                                   HTTP_IF_MODIFIED_SINCE=next_date)
        self.assertFalse(rv['errors'], msg=rv['errors'])
        self.assertEqual(rv['status'], '304 Not Modified')
        self.assertEqual(rv['data'], [])

        rv = handle_single_request('GET /img/logo.png',
                                   HTTP_IF_MODIFIED_SINCE=past_date)
        try:
            self.assertNoError(rv)
            data = b('').join([chunk for chunk in rv['data']])
            with open(os.path.join(rootdir, fname), 'rb') as f:
                self.assertEqual(data, f.read())
        finally:
            rv['data'].close()

    def test_send_file_head(self):
        fname = fiole.__file__
        rootdir, fname = os.path.split(fname)

        @fiole.get('/img/logo.png')
        def img_logo(request):
            return fiole.send_file(request, fname, root=rootdir)

        rv = handle_single_request('HEAD /img/logo.png')
        self.assertNoError(rv)
        self.assertEqual(rv['data'], [])
        hdrs = dict(rv['headers'])
        self.assertEqual(sorted(hdrs), ['Content-Length', 'Content-Type',
                                        'Last-Modified'])
        self.assertEqual(int(hdrs['Content-Length']),
                         os.path.getsize(fiole.__file__))

    def test_hook(self):
        captured = self.install_dummy_hook()
        body = ("acquire resource\npre-process request\n"
                "post-process response\nresponse = %s")

        @fiole.get('/')
        def index(request):
            return 'Hi!'

        rv = handle_single_request('GET /')
        self.assertNoError(rv)
        self.assertEqual(rv['data'], [b(body % 'Hi!')])
        self.assertEqual(rv['status'], '200 OK')
        self.assertEqual(captured, ['acquire resource',
                                    'pre-process request',
                                    'post-process response',
                                    'response = Hi!',
                                    'release resource'])
        del captured[:]

        rv = handle_single_request('GET /test_missing')
        self.assertEqual(rv['data'], [b(body % 'Not Found')])
        self.assertEqual(rv['status'], '404 Not Found')
        self.assertEqual(captured, ['acquire resource',
                                    'pre-process request',
                                    'post-process response',
                                    'response = Not Found',
                                    'release resource'])
        del captured[:]

    def test_hook_broken(self):
        captured = self.install_dummy_hook()

        @fiole.errorhandler(500)
        def broken_handler(request, age_du_capitaine):
            pass

        @fiole.get('/test_broken')
        def broken_route(request):
            return 42 / 0

        self.assertRaises(TypeError, handle_single_request, 'GET /test_broken')
        self.assertEqual(captured, ['acquire resource',
                                    'pre-process request',
                                    'release resource'])
        del captured[:]
