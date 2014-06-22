# -*- coding: utf-8 -*-
import fiole

__all__ = ['ENVIRON', 'FORM_DATA_CONTENT_TYPE', 'FORM_DATA_1', 'FORM_DATA_2',
           'PY3', 'handle_single_request']

ENVIRON = {
    'REQUEST_METHOD': 'GET',
    'PATH_INFO': '/',
    'QUERY_STRING': '',
    'CONTENT_TYPE': 'text/plain',
    'CONTENT_LENGTH': '',
    'HTTP_COOKIE': '',
    'SERVER_NAME': 'fakehost.invalid',
    'SERVER_PORT': '443',
    'wsgi.url_scheme': 'https',
}

# Samples from:
#   http://www.w3.org/TR/html401/interact/forms.html#h-17.13.4
FORM_DATA_CONTENT_TYPE = "multipart/form-data; boundary=AaB03x"
FORM_DATA_1 = b"""\
--AaB03x
Content-Disposition: form-data; name="submit-name"

Larry
--AaB03x
Content-Disposition: form-data; name="files"; filename="file1.txt"
Content-Type: text/plain

... contents of file1.txt ...
--AaB03x--"""
# Added "Content-Length: 268" to work around http://bugs.python.org/issue18013
FORM_DATA_2 = b"""\
--AaB03x
Content-Disposition: form-data; name="submit-name"

Larry
--AaB03x
Content-Disposition: form-data; name="files"
Content-Type: multipart/mixed; boundary=BbC04y
Content-Length: 268

--BbC04y
Content-Disposition: file; filename="file1.txt"
Content-Type: text/plain

... contents of file1.txt ...
--BbC04y
Content-Disposition: file; filename="file2.gif"
Content-Type: image/gif
Content-Transfer-Encoding: binary

...contents of file2.gif...
--BbC04y--
--AaB03x--"""

PY3 = (''.encode() != '')
basestring = str if PY3 else basestring
native = str if not PY3 else lambda s: s.decode('latin-1')


class FakeFile(list):
    def read(self, size):
        return (self.pop(0) if self else '').encode('utf-8')


class WSGIErrors(object):
    __slots__ = ('response',)

    def __init__(self, response):
        response['errors'] = ''
        self.response = response

    def write(self, text):
        self.response['errors'] += text


class StartResponse(object):
    __slots__ = ('response',)

    def __init__(self, response):
        self.response = response

    def __call__(self, status, response_headers, exc_info=None):
        assert 'status' not in self.response
        assert exc_info is None
        self.response['status'] = status
        self.response['headers'] = response_headers


def handle_single_request(environ, **kw):
    """Return a dictionary: {status, headers, data, errors}."""
    if isinstance(environ, basestring):
        method, sep, url = environ.encode('utf-8').partition(b' ')
        path, sep, query_string = url.partition(b'?')
        environ = dict(ENVIRON)
        environ.update({
            'REQUEST_METHOD': native(method),
            'PATH_INFO': native(path),
            'QUERY_STRING': native(query_string),
        })
    else:
        environ = dict(environ)
    rv = {}
    if kw:
        environ.update(kw)
    environ['wsgi.errors'] = WSGIErrors(rv)
    environ['wsgi.input'] = FakeFile()
    start_response = StartResponse(rv)
    rv['data'] = fiole.get_app().handle_request(environ, start_response)
    assert 'status' in rv
    return rv
