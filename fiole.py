#!/usr/bin/env python
""" The handy Python web framework.

Homepage: https://github.com/florentx/fiole/#readme
License: BSD (see LICENSE for details)
"""
import ast
import base64
import cgi
import hashlib
import hmac
import imp
import os
import re
import sys
import time
import threading
import traceback
from datetime import datetime, timedelta
from email.utils import mktime_tz, parsedate_tz
from functools import update_wrapper, wraps
from mimetypes import guess_type as guess_ct
from wsgiref.handlers import format_date_time, FileWrapper
try:                  # Python 3
    from http.client import responses as HTTP_CODES
    from http.cookies import SimpleCookie
    from io import BytesIO
    from urllib.parse import parse_qs
    unicode = str
    recode = lambda s: s.encode('iso-8859-1').decode('utf-8')
except ImportError:   # Python 2
    from httplib import responses as HTTP_CODES
    from Cookie import SimpleCookie
    from cStringIO import StringIO as BytesIO
    from urlparse import parse_qs
    unicode = unicode
    recode = lambda s: s.decode('utf-8')

DEFAULT_BIND = {'host': '127.0.0.1', 'port': 8080}
MAIN_MODULE = '__main__'

__version__ = '0.3.dev0'
__all__ = ['HTTPError', 'BadRequest', 'Forbidden', 'NotFound',  # HTTP errors
           'MethodNotAllowed', 'InternalServerError', 'Redirect',
           # Base classes
           'Accept', 'HTTPHeaders', 'EnvironHeaders', 'Request', 'Response',
           # Decorators
           'route', 'get', 'post', 'put', 'delete', 'errorhandler',
           # Template engine and static file helper
           'Loader', 'Lexer', 'Parser', 'BlockBuilder', 'Engine', 'Template',
           'engine', 'get_template', 'render_template', 'send_file',
           # WSGI application and server
           'Fiole', 'default_app', 'get_app', 'run_wsgiref', 'run_fiole']
_accept_re = re.compile(r'(?:^|,)\s*([^\s;,]+)(?:[^,]*?;\s*q=([\d.]*))?')


# Exceptions

class HTTPError(Exception):
    """Base exception for HTTP errors."""
    status = 404

    def __init__(self, message, hide_traceback=False):
        super(HTTPError, self).__init__(message)
        self.hide_traceback = hide_traceback


class BadRequest(HTTPError):
    status = 400

    def __init__(self, message, hide_traceback=True):
        super(BadRequest, self).__init__(message, hide_traceback)


class Forbidden(BadRequest):
    status = 403


class NotFound(BadRequest):
    status = 404


class MethodNotAllowed(BadRequest):
    status = 405


class InternalServerError(HTTPError):
    status = 500


class Redirect(HTTPError):
    """Redirect the user to a different URL."""
    status = 302

    def __init__(self, url):
        super(Redirect, self).__init__("Redirecting to '%s'..." % (url,),
                                       hide_traceback=True)
        self.url = url


# Helpers

def tobytes(value):
    """Convert a string argument to a byte string."""
    return value.encode('utf-8') if isinstance(value, unicode) else value


def escape_html(s):
    """Escape special chars in HTML string."""
    return cgi.escape(s).replace('"', '&quot;').replace("'", '&#x27;')


def format_timestamp(ts):
    """Format a timestamp in the format used by HTTP."""
    if isinstance(ts, datetime):
        ts = time.mktime(ts.utctimetuple())
    elif isinstance(ts, (tuple, time.struct_time)):
        ts = time.mktime(ts)
    try:
        return format_date_time(ts)
    except Exception:
        raise TypeError("Unknown timestamp type: %r" % ts)


def compare_digest(a, b):
    result = len(a) ^ len(b)
    for (x, y) in zip(a, b):
        result |= ord(x) ^ ord(y)
    return not result


def _create_signature(secret, *parts):
    sign = hmac.new(tobytes(secret), digestmod=hashlib.sha1)
    for part in parts:
        sign.update(tobytes(part))
    return sign.hexdigest()


def _get_root_folder():
    return os.path.abspath(os.path.dirname(
        getattr(sys.modules[MAIN_MODULE], '__file__', '.')))


def _url_matcher(url, _psub=re.compile(r'(<[a-zA-Z_]\w*>)').sub):
    if '(?' not in url:
        url = _psub(r'(?P\1[^/]+)', re.sub(r'([^<\w/>])', r'\\\1', url))
    return re.compile("^%s/$" % url.rstrip('/'), re.U).match


def _format_vkw(value, kw, _quoted=re.compile(r"[^\w!#$%&'*.^`|~+-]").search):
    if kw:
        for (k, v) in kw.items():
            value += '; ' + k.replace('_', '-')
            if v is not None:
                v = str(v)
                if _quoted(v):
                    v = '"%s"' % (v.replace('\\', '\\\\').replace('"', '\\"'))
                value += '=%s' % v
    if value and ('\n' in value or '\r' in value):
        raise ValueError('Invalid header, newline detected in %r' % value)
    return value


class lazyproperty(object):
    """A property whose value is computed only once."""

    def __init__(self, function):
        self._function = function
        update_wrapper(self, function)

    def __get__(self, obj, cls=None):
        if obj is None:
            return self
        value = self._function(obj)
        setattr(obj, self._function.__name__, value)
        return value


def lock_acquire(f):
    """Acquire a lock before executing the method.  Release after."""
    @wraps(f)
    def wrapper(self, *args, **kwargs):
        self.lock.acquire(1)
        try:
            return f(self, *args, **kwargs)
        finally:
            self.lock.release()
    return wrapper


class Accept(object):
    """Represent an ``Accept``-style header."""

    def __init__(self, header_name, value):
        accept_all = (not value and header_name != 'Accept-Encoding')
        self._parsed = list(self.parse(value)) if value else []
        self._masks = [('*', 1)] if accept_all else self._parsed
        if header_name == 'Accept-Language':
            self._match = self._match_language

    @staticmethod
    def parse(value):
        """Parse ``Accept``-style header."""
        for match in _accept_re.finditer(value):
            (name, quality) = match.groups()
            if name != 'q':
                try:
                    quality = float(quality or 1.)
                    if quality:
                        yield (name.lower(), min(1, quality))
                except ValueError:
                    yield (name.lower(), 1)

    def __bool__(self):
        return bool(self._parsed)
    __nonzero__ = __bool__

    def __iter__(self):
        for (mask, q) in sorted(self._parsed, key=lambda m: -m[1]):
            yield mask

    def __contains__(self, offer):
        """Return True if the given offer is listed in the accepted types."""
        assert '*' not in offer
        for (mask, q) in self._masks:
            if self._match(mask, offer):
                return True

    def quality(self, offer):
        """Return the quality of the given offer."""
        assert '*' not in offer
        bestq = 0
        for (mask, q) in self._parsed:
            if bestq < q and self._match(mask, offer):
                bestq = q
        return bestq or None

    def best_match(self, offers, default_match=None):
        """Return the best match in the sequence of offered types."""
        best_offer = (default_match, -1, '*')
        for offer in offers:
            server_quality = 1
            if isinstance(offer, (tuple, list)):
                (offer, server_quality) = offer
            assert '*' not in offer
            for (mask, q) in self._masks:
                possible_quality = server_quality * q
                if (possible_quality > best_offer[1] or
                    (possible_quality == best_offer[1] and
                     mask.count('*') < best_offer[2].count('*')
                     )) and self._match(mask, offer):
                    best_offer = (offer, possible_quality, mask)
        return best_offer[0]

    @staticmethod
    def _match(mask, offer):
        if mask.endswith('/*'):
            (mask, offer) = (mask[:-2], offer.split('/')[0])
        return (mask == '*' or mask == offer.lower())

    @staticmethod
    def _match_language(mask, offer):
        offer = offer.replace('_', '-').lower()
        return (mask == '*' or mask == offer or
                offer.startswith(mask + '-') or mask.startswith(offer + '-'))

    @classmethod
    def header(cls, header):
        def fget(request):
            return cls(header, request.headers[header])
        return lazyproperty(fget)


class HTTPHeaders(object):
    """An object that stores some headers."""

    def __init__(self, headers=None):
        self._list = []
        if headers is not None:
            if isinstance(headers, dict):
                headers = headers.items()
            self._list.extend(headers)

    def __len__(self):
        return len(self._list)

    def __iter__(self):
        """Yield ``(key, value)`` tuples."""
        return iter(self._list)

    def __getitem__(self, name):
        ikey = name.lower()
        for (k, v) in self._list:
            if k.lower() == ikey:
                return v

    def get(self, name, default=None):
        """Return the default value if the header doesn't exist."""
        rv = self[name]
        return rv if (rv is not None) else default

    def get_all(self, name):
        """Return a list of all the values for the header."""
        ikey = name.lower()
        return [v for (k, v) in self if k.lower() == ikey]

    def __delitem__(self, name):
        """Remove a header."""
        ikey = name.lower()
        self._list[:] = [(k, v) for (k, v) in self._list if k.lower() != ikey]

    def __contains__(self, name):
        """Check if this header is present."""
        return self[name] is not None

    def add(self, name, value, **kw):
        """Add a new header tuple to the list."""
        self._list.append((name, _format_vkw(value, kw)))

    def set(self, name, value, **kw):
        """Remove all header tuples for `key` and add a new one."""
        ikey = name.lower()
        _value = _format_vkw(value, kw)
        for idx, (old_key, old_value) in enumerate(self._list):
            if old_key.lower() == ikey:
                self._list[idx] = (name, _value)
                break
        else:
            return self._list.append((name, _value))
        self._list[idx + 1:] = [(k, v) for (k, v) in self._list[idx + 1:]
                                if k.lower() != ikey]
    __setitem__ = set

    def setdefault(self, name, value):
        """Add a new header if not present.  Return the value."""
        old_value = self[name]
        if old_value is not None:
            return old_value
        self.set(name, value)
        return value

    if str is unicode:
        def to_list(self, charset='iso-8859-1'):
            return [(k, str(v)) for (k, v) in self]
    else:
        def to_list(self, charset='iso-8859-1'):
            return [(k, v.encode(charset) if isinstance(v, unicode)
                     else str(v)) for (k, v) in self]
    to_list.__doc__ = """Convert the headers into a list."""

    def __str__(self, charset='iso-8859-1'):
        lines = ['%s: %s' % kv for kv in self.to_list(charset)]
        return '\r\n'.join(lines + ['', ''])

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, list(self))

    keys = lambda self: [k for (k, v) in self]
    values = lambda self: [v for (k, v) in self]
    items = lambda self: list(self)


class EnvironHeaders(HTTPHeaders):
    """Headers from a WSGI environment.  Read-only view."""

    def __init__(self, environ):
        self.environ = environ

    def __getitem__(self, name):
        key = name.upper().replace('-', '_')
        if key in ('CONTENT_TYPE', 'CONTENT_LENGTH'):
            return self.environ.get(key)
        return self.environ.get('HTTP_' + key)

    def __iter__(self):
        for (key, value) in self.environ.items():
            if key.startswith('HTTP_'):
                if key not in ('HTTP_CONTENT_TYPE', 'HTTP_CONTENT_LENGTH'):
                    yield (key[5:].replace('_', '-').title(), value)
            elif key in ('CONTENT_TYPE', 'CONTENT_LENGTH'):
                yield (key.replace('_', '-').title(), value)

    def __len__(self):
        return len([kv for kv in self])


# Request and Response

class Request(object):
    """An object to wrap the environ bits in a friendlier way."""

    def __init__(self, environ):
        self.environ = environ
        self.path = recode(environ.get('PATH_INFO', '/'))
        if self.path[-1:] != '/':
            self.path += '/'
        self.method = environ.get('REQUEST_METHOD', 'GET').upper()
        self.query = environ.get('QUERY_STRING', '')
        self.headers = EnvironHeaders(environ)
        try:
            self.content_length = int(self.headers['Content-Length'] or 0)
        except ValueError:
            self.content_length = 0
    accept = Accept.header('Accept')
    accept_charset = Accept.header('Accept-Charset')
    accept_encoding = Accept.header('Accept-Encoding')
    accept_language = Accept.header('Accept-Language')

    def __getattr__(self, name):
        """Access the environment."""
        return self.environ[name]

    @lazyproperty
    def GET(self):
        """A dictionary of GET parameters."""
        return self.build_get_dict()

    @lazyproperty
    def POST(self):
        """A dictionary of POST (or PUT) values, including files."""
        return self.build_complex_dict()
    PUT = POST

    @lazyproperty
    def body(self):
        """Content of the request."""
        return self.environ['wsgi.input'].read(self.content_length)

    @lazyproperty
    def cookies(self):
        """A dictionary of Cookie.Morsel objects."""
        cookies = SimpleCookie()
        try:
            cookies.load(self.headers["Cookie"])
        except Exception:
            pass
        return cookies

    def get_cookie(self, name, default=None):
        """Get the value of the cookie with the given name, else default."""
        if name in self.cookies:
            return self.cookies[name].value
        return default

    def get_secure_cookie(self, name, value=None, max_age_days=31):
        """Return the given signed cookie if it validates, or None."""
        if value is None:
            value = self.get_cookie(name)
        app = self.environ['fiole.app']
        return app.decode_signed(name, value, max_age_days=max_age_days)

    def build_get_dict(self):
        """Take GET data and rip it apart into a dict."""
        raw_query_dict = parse_qs(self.query, keep_blank_values=1)
        query_dict = {}

        for (key, value) in raw_query_dict.items():
            query_dict[key] = value if len(value) > 1 else value[0]
        return query_dict

    def build_complex_dict(self):
        """Take POST/PUT data and rip it apart into a dict."""
        environ = self.environ.copy()
        environ['QUERY_STRING'] = ''    # Don't mix GET and POST variables
        raw_data = cgi.FieldStorage(fp=BytesIO(self.body), environ=environ)
        post_dict = {}

        for field in raw_data:
            if isinstance(raw_data[field], list):
                post_dict[field] = [fs.value for fs in raw_data[field]]
            elif raw_data[field].filename:
                post_dict[field] = raw_data[field]  # We've got a file.
            else:
                post_dict[field] = raw_data[field].value
        return post_dict


class Response(object):
    charset = 'utf-8'

    def __init__(self, output, headers=None, status=200,
                 content_type='text/html', wrapped=False):
        self.output, self.status, self.wrapped = output, status, wrapped
        self.headers = HTTPHeaders(headers)
        if status != 304 and 'Content-Type' not in self.headers:
            if ';' not in content_type and (
                    content_type.startswith('text/') or
                    content_type == 'application/xml' or
                    (content_type.startswith('application/') and
                     content_type.endswith('+xml'))):
                content_type += '; charset=' + self.charset
            self.headers['Content-Type'] = content_type

    def set_cookie(self, name, value, domain=None, expires=None, path="/",
                   expires_days=None, signed=None, **kwargs):
        """Set the given cookie name/value with the given options."""
        name = str(name)
        value = value if isinstance(value, str) else value.encode('utf-8')
        if re.search(r"[\x00-\x20]", name + value):
            raise ValueError("Invalid cookie %r: %r" % (name, value))
        if expires_days is not None and not expires:
            expires = datetime.utcnow() + timedelta(days=expires_days)
        attrs = [("domain", domain), ("path", path),
                 ("expires", expires and format_timestamp(expires))]
        if "max_age" in kwargs:
            attrs.append(("max-age", kwargs.pop("max_age")))
        if not hasattr(self, "_new_cookie"):
            self._new_cookie = SimpleCookie()
        elif name in self._new_cookie:
            del self._new_cookie[name]
        self._new_cookie[name] = value if not signed else ""
        morsel = self._new_cookie[name]
        for (key, val) in attrs + list(kwargs.items()):
            morsel[key] = val or ""
        morsel._signed = signed and value

    def clear_cookie(self, name, path="/", domain=None):
        """Delete the cookie with the given name."""
        self.set_cookie(
            name, value="", path=path, expires_days=(-365), domain=domain)

    def set_secure_cookie(self, name, value, expires_days=30, **kwargs):
        """Sign and timestamp a cookie so it cannot be forged."""
        self.set_cookie(
            name, value, expires_days=expires_days, signed=True, **kwargs)

    def send(self, environ, start_response):
        """Send the headers and return the body of the response."""
        status = "%d %s" % (self.status, HTTP_CODES.get(self.status))
        body = (self.output if self.wrapped else
                [tobytes(self.output)]) if self.output else []
        if not self.wrapped:
            self.headers['Content-Length'] = str(body and len(body[0]) or 0)
        if hasattr(self, "_new_cookie"):
            app = environ['fiole.app']
            for cookie in self._new_cookie.values():
                if cookie._signed is not None:
                    self._new_cookie[cookie.key] = (
                        app.encode_signed(cookie.key, cookie._signed))
                self.headers.add("Set-Cookie", cookie.OutputString(None))
        start_response(status, self.headers.to_list())
        return body if environ['REQUEST_METHOD'] != 'HEAD' else []


class Fiole(object):
    """Web Application."""
    _stack = []
    static_folder = os.path.join(_get_root_folder(), 'static')

    def __init__(self):
        self.routes = []
        self.error_handlers = {302: http_302_found}
        self.debug = False

    @classmethod
    def push(cls, app=None):
        """Push a new :class:`Fiole` application on the stack."""
        cls._stack.append(app or cls())
        return cls._stack[-1]

    @classmethod
    def pop(cls, index=-1):
        """Remove the :class:`Fiole` application from the stack."""
        return cls._stack.pop(index)

    def handle_request(self, environ, start_response):
        """The main handler.  Dispatch to the user's code."""
        try:
            environ['fiole.app'] = self
            request = Request(environ)
            (callback, kwargs, status) = self.find_matching_url(request)
            response = callback(request, **kwargs)
        except Exception as exc:
            (response, status) = self.handle_error(exc, environ)
        if not isinstance(response, Response):
            response = Response(response, status=status)
        return response.send(environ, start_response)

    def handle_error(self, exception, environ, level=0):
        """Deal with the exception and present an error page."""
        status = getattr(exception, 'status', 500)
        if level > 2 or self.debug and status == 500:
            raise
        if not getattr(exception, 'hide_traceback', False):
            environ['wsgi.errors'].write("%s occurred on '%s': %s\n%s" % (
                exception.__class__.__name__, environ['PATH_INFO'],
                exception, traceback.format_exc()))
        handler = (self.error_handlers.get(status) or
                   self.default_error_handler(status))
        try:
            return handler(exception), status
        except HTTPError as exc:
            return self.handle_error(exc, environ, level + 1)

    def find_matching_url(self, request):
        """Search through the methods registered."""
        allowed_methods = set()
        for (regex, re_match, methods, callback, status) in self.routes:
            m = re_match(request.path)
            if m:
                if request.method in methods:
                    return (callback, m.groupdict(), status)
                allowed_methods.update(methods)
        if allowed_methods:
            raise MethodNotAllowed("The HTTP request method '%s' is "
                                   "not supported." % request.method)
        raise NotFound("Sorry, nothing here.")

    def encode_signed(self, name, value):
        """Return a signed string with timestamp."""
        value = base64.b64encode(tobytes(value)).decode('utf-8')
        timestamp = '%X' % time.time()
        signature = _create_signature(self.secret_key, name, value, timestamp)
        return (value + '|' + timestamp + '|' + signature)

    def decode_signed(self, name, value, max_age_days=31):
        """Decode a signed string with timestamp or return ``None``."""
        try:
            (value, timestamp, signed) = value.split('|')
        except (ValueError, AttributeError):
            return  # Invalid
        signature = _create_signature(self.secret_key, name, value, timestamp)
        if (compare_digest(signed, signature) and
                time.time() - int(timestamp, 16) < max_age_days * 86400):
            return base64.b64decode(value.encode('ascii')).decode('utf-8')

    def send_file(self, request, filename, root=None, content_type=None,
                  buffer_size=64 * 1024):
        """Fetch a static file from the filesystem."""
        if not filename:
            raise Forbidden("You must specify a file you'd like to access.")

        # Strip the '/' from the beginning/end and prevent jailbreak.
        valid_path = os.path.normpath(filename).strip('./')
        desired_path = os.path.join(root or self.static_folder, valid_path)

        if os.path.isabs(valid_path) or not os.path.exists(desired_path):
            raise NotFound("File does not exist.")
        if not os.access(desired_path, os.R_OK):
            raise Forbidden("You do not have permission to access this file.")
        stat = os.stat(desired_path)
        try:
            ims = parsedate_tz(request.headers['If-Modified-Since'].strip())
        except Exception:
            ims = None
        if ims and int(stat.st_mtime) <= mktime_tz(ims):    # 304 Not Modified
            return Response(None, status=304, wrapped=True)

        headers = {'Content-Length': str(stat.st_size),
                   'Last-Modified': format_timestamp(stat.st_mtime)}
        if not content_type:
            content_type = guess_ct(filename)[0] or 'application/octet-stream'
        file_wrapper = request.environ.get('wsgi.file_wrapper', FileWrapper)
        fobj = file_wrapper(open(desired_path, 'rb'), buffer_size)
        return Response(fobj, headers=headers, content_type=content_type,
                        wrapped=True)

    def default_error_handler(self, code):
        def error_handler(exception):
            return Response(message, status=code, content_type='text/plain')
        message = HTTP_CODES[code]
        self.error_handlers[code] = error_handler
        return error_handler

    # Decorators

    def route(self, url, methods=('GET', 'HEAD'), callback=None, status=200):
        """Register a method for processing requests."""
        def decorator(func, add=self.routes.append):
            add((url, _url_matcher(url), tuple(methods), func, status))
            return func
        return decorator(callback) if callback else decorator

    def get(self, url):
        """Register a method as capable of processing GET/HEAD requests."""
        return self.route(url, methods=('GET', 'HEAD'))

    def post(self, url):
        """Register a method as capable of processing POST requests."""
        return self.route(url, methods=('POST',))

    def put(self, url):
        """Register a method as capable of processing PUT requests."""
        return self.route(url, methods=('PUT',), status=201)

    def delete(self, url):
        """Register a method as capable of processing DELETE requests."""
        return self.route(url, methods=('DELETE',))

    def errorhandler(self, code):
        """Register a method for processing errors of a certain HTTP code."""
        def decorator(func):
            self.error_handlers[code] = func
            return func
        return decorator


def http_302_found(exception):
    return Response('', status=302, content_type='text/plain',
                    headers=[('Location', exception.url)])


def _make_app_wrapper(name):
    @wraps(getattr(Fiole, name))
    def wrapper(*args, **kwargs):
        return getattr(Fiole._stack[-1], name)(*args, **kwargs)
    return wrapper
send_file = _make_app_wrapper('send_file')
route = _make_app_wrapper('route')
get = _make_app_wrapper('get')
post = _make_app_wrapper('post')
put = _make_app_wrapper('put')
delete = _make_app_wrapper('delete')
errorhandler = _make_app_wrapper('errorhandler')

#: Get the :class:`Fiole` application which is on the top of the stack.
get_app = lambda: Fiole._stack[-1]
default_app = Fiole.push()

HTTP_CODES[418] = "I'm a teapot"                    # RFC 2324
HTTP_CODES[428] = "Precondition Required"
HTTP_CODES[429] = "Too Many Requests"
HTTP_CODES[431] = "Request Header Fields Too Large"
HTTP_CODES[511] = "Network Authentication Required"


# The template engine

SPECIAL_TOKENS = 'extends require # include import from def end'.split()
TOKENS = {'end' + k: 'end' for k in 'for if while with try class def'.split()}
TOKENS.update({k: 'compound' for k in 'for if while with try class'.split()})
TOKENS.update({k: 'continue' for k in 'else elif except finally'.split()})
TOKENS.update({k: k for k in SPECIAL_TOKENS})
COMPOUND_TOKENS = {'extends', 'def', 'compound'}
OUT_TOKENS = {'markup', 'var', 'include'}
isidentifier = re.compile(r'[a-zA-Z_]\w*').match
setdefs = "super_defs['?'] = ?; ? = local_defs.setdefault('?', ?)".replace


class Loader(object):
    """Load templates.

    ``templates`` - a dict where key corresponds to template name and
    value to template content.
    """
    template_folder = 'templates'

    def __init__(self, templates=None):
        self.templates = templates if templates is not None else {}

    def list_names(self):
        """List all keys from internal dict."""
        return tuple(sorted(self.templates))

    def load(self, name, source=None):
        """Return template by name."""
        if source is not None:
            return unicode(source)
        if name in self.templates:
            return self.templates[name]
        path = os.path.join(_get_root_folder(), self.template_folder, name)
        with open(path, 'rb') as f:
            return f.read().decode('utf-8')


class Lexer(object):
    """Tokenize input source per rules supplied."""

    def __init__(self, lexer_rules):
        """Initialize with ``rules``."""
        self.rules = lexer_rules

    def tokenize(self, source):
        """Translate ``source`` into an iterable of tokens."""
        tokens = []
        source = source.replace('\r\n', '\n')
        (pos, lineno, end, append) = (0, 1, len(source), tokens.append)
        while pos < end:
            for tokenizer in self.rules:
                rv = tokenizer(source, pos)
                if rv:
                    (npos, token, value) = rv
                    break
            else:
                raise SyntaxError('Lexer pattern mismatch.')
            assert npos > pos
            append((lineno, token, value))
            lineno += source[pos:npos].count('\n')
            pos = npos
        return tokens


class Parser(Lexer):
    """Include basic statements, variables processing and markup."""

    def __init__(self, token_start='%', var_start='{{', var_end='}}',
                 line_join='\\'):
        d = {'tok': re.escape(token_start), 'lj': re.escape(line_join),
             'vs': re.escape(var_start), 've': re.escape(var_end)}
        stmt_match = re.compile(r' *%(tok)s(?!%(tok)s) *(#|\w+ ?)? *'
                                r'(.*?)(?<!%(lj)s)(?:\n|$)' % d, re.S).match
        var_match = re.compile(r'%(vs)s\s*(.*?)\s*%(ve)s' % d, re.S).match
        markup_match = re.compile(r'.*?(?:(?=%(vs)s)|\n(?= *%(tok)s'
                                  r'[^%(tok)s]))|.+' % d, re.S).match
        line_join_sub = re.compile(r'%(lj)s\n' % d).sub

        def stmt_token(source, pos):
            """Produce statement token."""
            m = stmt_match(source, pos)
            if m:
                if pos > 0 and source[pos - 1] != '\n':
                    return
                token = m.group(1) or ''
                stmt = token + line_join_sub('', m.group(2))
                token = TOKENS.get(token.rstrip(), 'statement')
                if token in ('require', 'include', 'extends'):
                    stmt = re.search(r'\(\s*(.*?)\s*\)', stmt).group(1)
                    if token == 'require':
                        stmt = re.findall(r'([^\s,]+)[\s,]*', stmt)
                return (m.end(), token, stmt)

        def var_token(source, pos):
            """Produce variable token."""
            m = var_match(source, pos)
            return m and (m.end(), 'var', line_join_sub('', m.group(1)))

        def mtok(source, pos, _s=re.compile(r'(\n *%(tok)s)%(tok)s' % d).sub):
            """Produce markup token."""
            m = markup_match(source, pos)
            return m and (m.end(), 'markup', line_join_sub('', _s(r'\1',
                          (source[pos-1] if pos else '\n') + m.group())[1:]))

        super(Parser, self).__init__([stmt_token, var_token, mtok])

    def end_continue(self, tokens):
        """If token is ``continue`` prepend it with ``end`` token so
        it simulates a closed block.
        """
        for (lineno, token, value) in tokens:
            if token == 'continue':
                yield lineno, 'end', None
                token = 'compound'
            yield lineno, token, value

    def parse_iter(self, tokens):
        """Process and yield groups of tokens."""
        operands = []
        for (lineno, token, value) in tokens:
            if token in OUT_TOKENS:
                operands.append((lineno, token, value))
                continue
            if operands:
                yield operands[0][0], 'out', operands
                operands = []
            if token in COMPOUND_TOKENS:
                vals = list(self.parse_iter(tokens))
                if token != 'extends' and vals and vals[-1][1] != 'end':
                    raise SyntaxError('Missing "end" statement at line %d.' %
                                      vals[-1][0])
                value = (value, vals)
            yield lineno, token, value
            if token == 'end':
                break
        if operands:
            yield operands[0][0], 'out', operands


class BlockBuilder(list):

    filters = {'s': 'str', 'e': 'escape'}
    writer_declare = '_b = []; w = _b.append'
    writer_return = "return ''.join(_b)"

    def __init__(self, indent='', lineno=0, nodes=()):
        self.indent = indent
        self.lineno = self.offset = lineno
        self.local_vars = set()
        self.build_block(nodes)

    def __enter__(self):
        self.indent += '    '

    def __exit__(self, exc_type, exc_value, exc_tb):
        self.indent = self.indent[:-4]

    def add(self, lineno, code, token='statement'):
        """Add Python code to the source."""
        assert lineno >= self.lineno
        if code == 'return':
            code = self.writer_return
        if lineno > self.lineno:
            pad = lineno - self.lineno - 1
            if pad > 0:
                self.extend([''] * pad)
            self.append((self.indent + code) if code else '')
        elif code:
            if not self[-1]:
                self[-1] = self.indent
            elif self[-1][-1:] != ':':
                self[-1] += '; '
            self[-1] += code
        self.lineno = lineno + code.count('\n')
        return self     # Convenient for the context manager API

    def build_block(self, nodes):
        for (lineno, token, value) in nodes:
            self.build_token(lineno, value, token)
        return True

    def build_token(self, lineno, value, token):
        assert token in self.rules, ('No rule to build "%s" token '
                                     'at line %d.' % (token, lineno))
        return any(r(self, lineno, value, token) for r in self.rules[token])

    def compile_code(self, name):
        """Compile the generated source code."""
        source = compile('\n'.join(self), name, 'exec', ast.PyCF_ONLY_AST)
        ast.increment_lineno(source, self.offset)
        return compile(source, name, 'exec')

    # all builder rules

    def build_extends(self, lineno, nodes, token):
        assert token == 'render'
        if len(nodes) not in (1, 2):    # Ignore 'require' before 'extends'
            return
        (lineno, token, value) = nodes[-1]
        if token != 'extends':
            return
        (extends, nodes) = value
        stmt = 'return _r(' + extends + ', ctx, local_defs, super_defs)'
        self.build_block([n for n in nodes if n[1] in ('def', 'require')])
        return self.add(self.lineno + 1, stmt)

    def build_import(self, lineno, value, token):
        assert token == 'import'
        parts = value[7:].rsplit(None, 2)
        if len(parts) == 3 and parts[1] == 'as':
            if parts[0] in self.local_vars or not isidentifier(parts[0]):
                value = "%s = _i(%s)" % (parts[2], parts[0])
        return self.add(lineno, value)

    def build_from(self, lineno, value, token):
        assert token == 'from'
        (name, tok2, var) = value[5:].rsplit(None, 2)
        alias = var
        if tok2 == 'as':
            (name, tok2, var) = name.rsplit(None, 2)
        assert tok2 == 'import'
        if name in self.local_vars or not isidentifier(name):
            value = "%s = _i(%s).local_defs['%s']" % (alias, name, var)
        return self.add(lineno, value)

    def build_render_single_markup(self, lineno, nodes, token):
        assert token == 'render' and lineno <= 0
        if not nodes:
            return self.add(lineno, "return ''")
        if len(nodes) == 1:
            (ln, token, nodes) = nodes[0]
            if token == 'out' and len(nodes) == 1:
                (ln, token, value) = nodes[0]
                if token == 'markup':
                    return self.add(ln, "return %r" % value)

    def build_render(self, lineno, nodes, token):
        assert token == 'render' and lineno <= 0
        self.add(lineno, self.writer_declare)
        self.build_block(nodes)
        return self.add(self.lineno + 1, self.writer_return)

    def build_def_single_markup(self, lineno, value, token):
        assert token == 'def'
        (stmt, nodes) = value
        (ln, token, subnodes) = nodes[0]
        if token in COMPOUND_TOKENS:
            error = ("The compound statement '%s' is not allowed here. "
                     "Add a line before it with %%#ignore.\n\n%s\n"
                     "    %%#ignore\n    %%%s ..." % (token, stmt, token))
            with self.add(lineno, stmt):
                return self.add(ln, 'raise SyntaxError(%r)' % error)
        if len(nodes) > 2:
            return
        (ln, value) = (lineno, '')
        if len(nodes) == 2:
            if token != 'out' or len(subnodes) > 1:
                return
            (ln, token, value) = subnodes[0]
            if token != 'markup':
                return
        with self.add(lineno, stmt):
            self.add(ln, "return " + repr(value))
        return self.add(ln + 1, setdefs('?', stmt[4:stmt.index('(', 5)]))

    def build_def(self, lineno, value, token):
        assert token == 'def'
        (stmt, nodes) = value
        with self.add(lineno, stmt):
            self.add(lineno + 1, self.writer_declare)
            self.build_block(nodes)
            ln = self.lineno
            self.add(ln, self.writer_return)
        return self.add(ln + 1, setdefs('?', stmt[4:stmt.index('(', 5)]))

    def build_out(self, lineno, nodes, token):
        assert token == 'out'
        for (lineno, token, value) in nodes:
            if token == 'include':
                value = '_r(' + value + ', ctx, local_defs, super_defs)'
            elif token == 'var':
                if '|' in value:
                    filters = [f.strip() for f in value.split('|')]
                    value = filters.pop(0)
                    for f in filters:
                        value = self.filters.get(f, f) + '(' + value + ')'
            elif value:
                value = repr(value)
            if value:
                self.add(lineno, 'w(' + value + ')')

    def build_compound(self, lineno, value, token):
        assert token == 'compound'
        (stmt, nodes) = value
        with self.add(lineno, stmt):
            return self.build_block(nodes)

    def build_require(self, lineno, values, token):
        stmt = '; '.join([v + " = ctx['" + v + "']"
                          for v in values if v not in self.local_vars])
        self.local_vars.update(values)
        return self.add(lineno, stmt)

    def build_end(self, lineno, value, token):
        if self.lineno != lineno:
            self.add(lineno - 1, '')

    rules = {
        'render': [build_extends, build_render_single_markup, build_render],
        'def': [build_def_single_markup, build_def],
        'statement': [add],
        '#': [],
    }
    for name in ('import', 'from', 'require', 'out', 'compound', 'end'):
        rules[name] = [locals()['build_' + name]]


class Engine(object):
    """Assemble the template engine."""

    def __init__(self, loader=None, parser=None, template_class=None):
        self.lock = threading.Lock()
        self.clear()
        self.global_vars = {'_r': self.render, '_i': self.import_name}
        self.template_class = template_class or Template
        self.loader = loader or Loader()
        self.parser = parser or Parser()

    def clear(self):
        """Remove all compiled templates from the internal cache."""
        self.templates, self.renders, self.modules = {}, {}, {}

    def get_template(self, name=None, **kwargs):
        """Return a compiled template."""
        if name and kwargs:
            self.remove(name)
        try:
            return self.templates[name]
        except KeyError:
            return self.compile_template(name, **kwargs)

    @lock_acquire
    def remove(self, name):
        """Remove given ``name`` from the internal cache."""
        if name in self.renders:
            del self.templates[name], self.renders[name]
        if name in self.modules:
            del self.modules[name]

    def render(self, name, ctx, local_defs, super_defs):
        """Render template by name in given context."""
        try:
            return self.renders[name](ctx, local_defs, super_defs)
        except KeyError:
            self.compile_template(name)
        return self.renders[name](ctx, local_defs, super_defs)

    def import_name(self, name, **kwargs):
        """Compile and return a template as module."""
        try:
            return self.modules[name]
        except KeyError:
            self.compile_import(name, **kwargs)
        return self.modules[name]

    @lock_acquire
    def compile_template(self, name, **kwargs):
        if name in self.templates:
            return self.templates[name]
        nodes = self.load_and_parse(name, **kwargs)
        def_render = 'def render(ctx, local_defs, super_defs):'
        nodes = [(-1, 'compound', (def_render, [(0, 'render', list(nodes))]))]
        source = BlockBuilder(lineno=-2, nodes=nodes)
        compiled = source.compile_code(name or '<string>')
        local_vars = {}
        exec(compiled, self.global_vars, local_vars)
        template = self.template_class(name, local_vars['render'])
        if name:
            self.templates[name] = template
            self.renders[name] = template.render_template
        return template

    @lock_acquire
    def compile_import(self, name, **kwargs):
        if name not in self.modules:
            nodes = self.load_and_parse(name, **kwargs)
            nodes = ([(-1, 'statement', 'local_defs = {}; super_defs = {}')] +
                     [n for n in nodes if n[1] == 'def'])
            source = BlockBuilder(lineno=-2, nodes=nodes)
            compiled = source.compile_code(name)
            self.modules[name] = module = imp.new_module(name)
            module.__dict__.update(self.global_vars)
            exec(compiled, module.__dict__)

    def load_and_parse(self, name, **kwargs):
        template_source = self.loader.load(name, **kwargs)
        tokens = self.parser.tokenize(template_source)
        return self.parser.parse_iter(self.parser.end_continue(tokens))


class Template(object):
    """Simple template class."""
    __slots__ = ('name', 'render_template')

    def __init__(self, name, render_template):
        (self.name, self.render_template) = (name, render_template)

    def render(self, ctx=None, **kwargs):
        if ctx and kwargs:
            ctx = dict(ctx, **kwargs)
        return self.render_template(ctx or kwargs, {}, {})

engine = Engine()
engine.global_vars.update({'str': unicode, 'escape': escape_html})


def get_template(name=None, source=None, require=None):
    """Return a compiled template."""
    if get_app().debug:
        engine.clear()
    if source is None:
        if '\n' not in name and '{{' not in name:
            return engine.get_template(name)
        (name, source) = (None, name)
    if require:
        source = "%require(" + " ".join(require) + ")\n" + source
    return engine.get_template(name, source=source)


def render_template(template_name=None, source=None, **context):
    """Render a template with values of the *context* dictionary."""
    return get_template(template_name, source, context).render(context)


# The WSGI HTTP server

def run_wsgiref(host, port, handler):
    """Simple HTTPServer that supports WSGI."""
    from wsgiref.simple_server import make_server, ServerHandler

    def cleanup_headers(self):
        # work around http://bugs.python.org/issue18099
        if self.status[:3] == "304":
            del self.headers['Content-Length']
        elif 'Content-Length' not in self.headers:
            self.set_content_length()
    ServerHandler.cleanup_headers = cleanup_headers

    srv = make_server(host, port, handler)
    srv.serve_forever()


def run_fiole(app=default_app, server=run_wsgiref, host=None, port=None):
    """Run the *Fiole* web server."""
    if not hasattr(app, 'secret_key'):
        app.secret_key = base64.b64encode(os.urandom(33))
    assert app.routes, "No route defined"
    host = host or DEFAULT_BIND['host']
    port = int(port or DEFAULT_BIND['port'])
    print('`fiole` starting up (using %s)...\nListening on http://%s:%s...\n'
          'Use Ctrl-C to quit.\n' % (server.__name__, host, port))

    try:
        server(host, port, app.handle_request)
    except KeyboardInterrupt:
        print('\nShutting down.  Have a nice day!')
        raise SystemExit(0)


if __name__ == '__main__':
    import optparse
    parser = optparse.OptionParser(version=__version__,
                                   usage="%prog [options] package.module:app")
    parser.add_option('-p', '--port', default='127.0.0.1:8080',
                      help='bind to (default: %default)')
    (options, args) = parser.parse_args()
    (host, sep, port) = options.port.rpartition(':')
    if len(args) != 1:
        parser.error('a single positional argument is required')
    DEFAULT_BIND.update(host=host or DEFAULT_BIND['host'], port=int(port))
    (MAIN_MODULE, sep, target) = args[0].partition(':')
    sys.path[:0] = ['.']
    sys.modules.setdefault('fiole', sys.modules['__main__'])

    # Load and run server application
    __import__(MAIN_MODULE)
    Fiole.static_folder = os.path.join(_get_root_folder(), 'static')
    (getattr(sys.modules[MAIN_MODULE], target) if target else run_fiole)()
