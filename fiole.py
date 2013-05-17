#!/usr/bin/env python
""" The handy Python web framework.

Homepage: https://github.com/florentx/fiole/#readme
License: BSD (see LICENSE for details)
"""
import ast
import base64
import cgi
import Cookie
import hashlib
import hmac
import imp
import mimetypes
import os
import re
import time
import traceback
from cStringIO import StringIO
from datetime import datetime, timedelta
from email.utils import formatdate
from functools import wraps
from httplib import responses as HTTP_CODES
from threading import Lock
from urlparse import parse_qs
from wsgiref.util import FileWrapper

DEFAULT_BIND = {'host': '127.0.0.1', 'port': 8080}
STATIC_FOLDER = os.path.join(os.path.dirname(__file__), 'static')
TEMPLATE_FOLDER = os.path.join(os.path.dirname(__file__), 'templates')
HTTP_CODES[418] = "I'm a teapot"                    # RFC 2324
HTTP_CODES[428] = "Precondition Required"
HTTP_CODES[429] = "Too Many Requests"
HTTP_CODES[431] = "Request Header Fields Too Large"
HTTP_CODES[511] = "Network Authentication Required"
COOKIE_SECRET = None
REQUEST_RULES = []
ERROR_HANDLERS = {}

__version__ = '0.1a0'
__all__ = ['HTTPError', 'BadRequest', 'Forbidden', 'NotFound',  # HTTP errors
           'MethodNotAllowed', 'InternalServerError', 'Redirect',
           # Base classes and static file helper
           'HTTPHeaders', 'EnvironHeaders', 'Request', 'Response', 'send_file',
           # Decorators
           'route', 'get', 'post', 'put', 'delete', 'errorhandler',
           # Template engine
           'Loader', 'Lexer', 'Parser', 'BlockBuilder', 'Engine', 'Template',
           'engine', 'get_template', 'render_template',
           # WSGI application
           'handle_request', 'run_fiole']


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


def format_timestamp(ts):
    """Format a timestamp in the format used by HTTP."""
    if isinstance(ts, datetime):
        ts = time.mktime(ts.utctimetuple())
    elif isinstance(ts, (tuple, time.struct_time)):
        ts = time.mktime(ts)
    try:
        return formatdate(ts, usegmt=True)
    except Exception:
        raise TypeError("Unknown timestamp type: %r" % ts)


def compare_digest(a, b):
    result = len(a) ^ len(b)
    for x, y in zip(a, b):
        result |= ord(x) ^ ord(y)
    return not result


def _create_signed_value(secret, name, value):
    value = base64.b64encode(tobytes(value))
    timestamp = '%X' % time.time()
    signature = _create_signature(secret, name, value, timestamp)
    return (value + '|' + timestamp + '|' + signature)


def _decode_signed_value(secret, name, value, max_age_days=31):
    parts = tobytes(value or '').split("|")
    if len(parts) != 3:
        return  # Invalid
    if time.time() - int(parts[1], 16) > max_age_days * 86400:
        return  # Expired
    signature = _create_signature(secret, name, parts[0], parts[1])
    if compare_digest(parts[2], signature):
        return base64.b64decode(parts[0])


def _create_signature(secret, *parts):
    sign = hmac.new(tobytes(secret), digestmod=hashlib.sha1)
    for part in parts:
        sign.update(tobytes(part))
    return sign.hexdigest()


def _url_matcher(url):
    regex = (url if url[-1:] == '/' else url + '/')
    return re.compile("^%s$" % regex, re.U).match


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
    __slots__ = ('_function',)

    def __init__(self, function):
        self._function = function

    def __get__(self, obj, cls=None):
        if obj is None:
            return self
        value = self._function(obj)
        setattr(obj, self._function.func_name, value)
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
        """Return the default value if the requested data doesn't exist."""
        rv = self[name]
        return rv if (rv is not None) else default

    def get_all(self, name):
        """Return a list of all the values for the named field."""
        ikey = name.lower()
        return [v for (k, v) in self if k.lower() == ikey]

    def __delitem__(self, name):
        """Remove a key."""
        ikey = name.lower()
        self._list[:] = [(k, v) for (k, v) in self._list if k.lower() != ikey]

    def __contains__(self, key):
        """Check if a key is present."""
        return self[key] is not None

    def add(self, _key, _value, **kw):
        """Add a new header tuple to the list."""
        self._list.append((_key, _format_vkw(_value, kw)))

    def set(self, _key, _value, **kw):
        """Remove all header tuples for `key` and add a new one."""
        ikey = _key.lower()
        _value = _format_vkw(_value, kw)
        for idx, (old_key, old_value) in enumerate(self._list):
            if old_key.lower() == ikey:
                self._list[idx] = (_key, _value)
                break
        else:
            return self._list.append((_key, _value))
        self._list[idx + 1:] = [(k, v) for (k, v) in self._list[idx + 1:]
                                if k.lower() != ikey]
    __setitem__ = set

    def setdefault(self, key, value):
        old_value = self[key]
        if old_value is not None:
            return old_value
        self.set(key, value)
        return value

    def to_list(self, charset='iso-8859-1'):
        """Convert the headers into a list."""
        return [(k, v.encode(charset) if isinstance(v, unicode) else str(v))
                for (k, v) in self]

    def __str__(self, charset='iso-8859-1'):
        lines = ['%s: %s' % kv for kv in self.to_list(charset)]
        return '\r\n'.join(lines + ['', ''])

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, list(self))

    keys = lambda self: [k for (k, v) in self]
    values = lambda self: [v for (k, v) in self]
    items = lambda self: list(self)


class EnvironHeaders(HTTPHeaders):
    """Headers from a WSGI environment."""

    def __init__(self, environ):
        self.environ = environ

    def __getitem__(self, key):
        key = key.upper().replace('-', '_')
        if key in ('CONTENT_TYPE', 'CONTENT_LENGTH'):
            return self.environ.get(key)
        return self.environ.get('HTTP_' + key)

    def __iter__(self):
        for key, value in self.environ.iteritems():
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
        self.path = environ.get('PATH_INFO', '/').decode('utf-8')
        if self.path[-1:] != '/':
            self.path += '/'
        self.method = environ.get('REQUEST_METHOD', 'GET').upper()
        self.query = environ.get('QUERY_STRING', '')
        self.headers = EnvironHeaders(environ)
        try:
            self.content_length = int(self.headers['Content-Length'] or 0)
        except ValueError:
            self.content_length = 0

    def __getattr__(self, name):
        """Access the environment."""
        return self.environ[name]

    @lazyproperty
    def GET(self):
        return self.build_get_dict()

    @lazyproperty
    def POST(self):
        return self.build_complex_dict()

    @lazyproperty
    def PUT(self):
        return self.build_complex_dict()

    @lazyproperty
    def body(self):
        """Content of the request."""
        return self.environ['wsgi.input'].read(self.content_length)

    @lazyproperty
    def cookies(self):
        """A dictionary of Cookie.Morsel objects."""
        cookies = Cookie.SimpleCookie()
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
        return _decode_signed_value(COOKIE_SECRET, name, value,
                                    max_age_days=max_age_days)

    def build_get_dict(self):
        """Take GET data and rip it apart into a dict."""
        raw_query_dict = parse_qs(self.query, keep_blank_values=1)
        query_dict = {}

        for key, value in raw_query_dict.items():
            query_dict[key] = value if len(value) > 1 else value[0]
        return query_dict

    def build_complex_dict(self):
        """Take POST/PUT data and rip it apart into a dict."""
        environ = self.environ.copy()
        environ['QUERY_STRING'] = ''    # Don't mix GET and POST variables
        raw_data = cgi.FieldStorage(fp=StringIO(self.body), environ=environ)
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
        if ';' not in content_type and (
                content_type.startswith('text/') or
                content_type == 'application/xml' or
                (content_type.startswith('application/') and
                 content_type.endswith('+xml'))):
            content_type += '; charset=' + self.charset
        self.headers['Content-Type'] = content_type

    def set_cookie(self, name, value, domain=None, expires=None, path="/",
                   expires_days=None, **kwargs):
        """Set the given cookie name/value with the given options."""
        name = tobytes(name)
        value = tobytes(value)
        if re.search(r"[\x00-\x20]", name + value):
            raise ValueError("Invalid cookie %r: %r" % (name, value))
        if not hasattr(self, "_new_cookie"):
            self._new_cookie = Cookie.SimpleCookie()
        if name in self._new_cookie:
            del self._new_cookie[name]
        self._new_cookie[name] = value
        morsel = self._new_cookie[name]
        if domain:
            morsel["domain"] = domain
        if expires_days is not None and not expires:
            expires = datetime.utcnow() + timedelta(days=expires_days)
        if expires:
            morsel["expires"] = format_timestamp(expires)
        if path:
            morsel["path"] = path
        for (k, v) in kwargs.items():
            if k == 'max_age':
                k = 'max-age'
            morsel[k] = v

    def clear_cookie(self, name, path="/", domain=None):
        """Delete the cookie with the given name."""
        expires = datetime.utcnow() - timedelta(days=365)
        self.set_cookie(name, value="", path=path, expires=expires,
                        domain=domain)

    def set_secure_cookie(self, name, value, expires_days=30, **kwargs):
        """Sign and timestamp a cookie so it cannot be forged."""
        self.set_cookie(name, self.create_signed_value(name, value),
                        expires_days=expires_days, **kwargs)

    def create_signed_value(self, name, value):
        """Sign and timestamp a string so it cannot be forged."""
        return _create_signed_value(COOKIE_SECRET, name, value)

    def send(self, environ, start_response):
        status = "%d %s" % (self.status, HTTP_CODES.get(self.status))
        output = self.output if self.wrapped else [tobytes(self.output or '')]
        if not self.wrapped:
            self.headers['Content-Length'] = str(len(output[0]))
        if hasattr(self, "_new_cookie"):
            for cookie in self._new_cookie.values():
                self.headers.add("Set-Cookie", cookie.OutputString(None))
        start_response(status, self.headers.to_list())
        return output if (environ['REQUEST_METHOD'] != 'HEAD') else ()


def handle_request(environ, start_response):
    """The main handler.  Dispatch to the user's code."""
    try:
        request = Request(environ)
        (callback, kwargs, status) = find_matching_url(request)
        response = callback(request, **kwargs)
    except Exception as exc:
        (response, status) = handle_error(exc, environ)
    if not isinstance(response, Response):
        response = Response(response, status=status)
    return response.send(environ, start_response)


def handle_error(exception, environ, level=0):
    """If an exception is thrown, deal with it and present an error page."""
    if not getattr(exception, 'hide_traceback', False):
        environ['wsgi.errors'].write("%s occurred on '%s': %s\n%s" % (
            exception.__class__.__name__, environ['PATH_INFO'],
            exception, traceback.format_exc()))
    status = getattr(exception, 'status', 500)
    handler = ERROR_HANDLERS.get(status) or default_error_handler(status)
    try:
        return handler(exception), status
    except Exception as exc:
        if level > 3:
            raise
        return handle_error(exc, environ, level + 1)


def find_matching_url(request):
    """Search through the methods registered."""
    allowed_methods = set()
    for (regex, re_match, methods, callback, status) in REQUEST_RULES:
        m = re_match(request.path)
        if m:
            if request.method in methods:
                return (callback, m.groupdict(), status)
            allowed_methods.update(methods)
    if allowed_methods:
        raise MethodNotAllowed("The HTTP request method '%s' is "
                               "not supported." % request.method)
    raise NotFound("Sorry, nothing here.")


# Serve static file

def send_file(request, filename, root=STATIC_FOLDER,
              content_type=None, buffer_size=64 * 1024):
    """Fetch a static file from the filesystem."""
    if not filename:
        raise Forbidden("You must specify a file you'd like to access.")

    # Strip the '/' from the beginning/end and prevent jailbreak.
    valid_path = os.path.normpath(filename).strip('./')
    desired_path = os.path.join(root, valid_path)

    if os.path.isabs(valid_path) or not os.path.exists(desired_path):
        raise NotFound("File does not exist.")
    if not os.access(desired_path, os.R_OK):
        raise Forbidden("You do not have permission to access this file.")
    stat = os.stat(desired_path)
    headers = {'Content-Length': str(stat.st_size),
               'Last-Modified': format_timestamp(stat.st_mtime)}

    if not content_type:
        content_type = mimetypes.guess_type(filename)[0] or 'text/plain'
    file_wrapper = request.environ.get('wsgi.file_wrapper', FileWrapper)
    fobj = file_wrapper(open(desired_path, 'rb'), buffer_size)
    return Response(fobj, headers=headers, content_type=content_type,
                    wrapped=True)


# Decorators

def route(url, methods=('GET',), status=200):
    def decorator(func):
        REQUEST_RULES.append((url, _url_matcher(url), methods, func, status))
        return func
    return decorator


def get(url):
    """Register a method as capable of processing GET requests."""
    return route(url, methods=('GET', 'HEAD'))


def post(url):
    """Register a method as capable of processing POST requests."""
    return route(url, methods=('POST',))


def put(url):
    """Register a method as capable of processing PUT requests."""
    return route(url, methods=('PUT',), status=201)


def delete(url):
    """Register a method as capable of processing DELETE requests."""
    return route(url, methods=('DELETE',))


def errorhandler(code):
    """Register a method for processing errors of a certain HTTP code."""
    def decorator(func):
        ERROR_HANDLERS[code] = func
        return func
    return decorator


# Error handlers

def default_error_handler(code):
    def error_handler(exception):
        return Response(message, status=code, content_type='text/plain')
    message = HTTP_CODES[code]
    ERROR_HANDLERS[code] = error_handler
    return error_handler


@errorhandler(302)
def http_302_found(exception):
    return Response('', status=302, content_type='text/plain',
                    headers=[('Location', exception.url)])


# The template engine

BLOCK_TOKENS = ['for', 'if', 'while', 'with', 'try', 'def', 'class']
CONTINUE_TOKENS = ['else', 'elif', 'except', 'finally']
END_TOKENS = ['end'] + ['end' + w for w in BLOCK_TOKENS]
RESERVED_TOKENS = ['extends', 'require', '#', 'include', 'import', 'from']
ALL_TOKENS = BLOCK_TOKENS + CONTINUE_TOKENS + END_TOKENS + RESERVED_TOKENS
COMPOUND_TOKENS = ['extends', 'def', 'block', 'continue']
OUT_TOKENS = ['markup', 'var', 'include']
isidentifier = re.compile(r'[a-zA-Z_]\w*').match


class Loader(object):
    """Load templates.

    ``templates`` - a dict where key corresponds to template name and
    value to template content.
    """

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
        path = os.path.join(TEMPLATE_FOLDER, name)
        with open(path, 'rb') as f:
            return f.read().decode('utf-8')


class Lexer(object):
    """Tokenize input source per rules supplied."""

    def __init__(self, lexer_rules, preprocessors=None, **ignore):
        """Initialize with ``rules``."""
        self.rules = lexer_rules
        self.preprocessors = preprocessors or []

    def tokenize(self, source):
        """Translate ``source`` into an iterable of tokens."""
        tokens = []
        append = tokens.append
        for preprocessor in self.preprocessors:
            source = preprocessor(source)
        pos, lineno, end = 0, 1, len(source)
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
        tok = re.escape(token_start)
        vstart, vend = re.escape(var_start), re.escape(var_end)
        _clean = re.compile(r'(^|\n)(?: +)(?=%s[^%s])' % (tok, tok)).sub
        stmt_match = re.compile(r'%s *(\w+ ?|#) *(.*?(?<!%s))(?:\n|$)' %
                                (tok, re.escape(line_join)), re.S).match
        var_match = re.compile(r'%s\s*(.*?)\s*%s' % (vstart, vend)).match
        markup_match = re.compile(r'.*?(?:(?=%s)|\n *(?=%s[^%s]))|.+' %
                                  (vstart, tok, tok), re.S).match
        line_join += '\n'

        def stmt_token(source, pos):
            """Produce statement token."""
            m = stmt_match(source, pos)
            if m:
                if pos > 0 and source[pos - 1] != '\n':
                    return
                token = m.group(1)
                stmt = token + m.group(2).replace(line_join, '')
                token = token.rstrip()
                if token in END_TOKENS:
                    token = 'end'
                elif token in CONTINUE_TOKENS:
                    token = 'continue'
                elif token in BLOCK_TOKENS and token != 'def':
                    token = 'block'
                elif token not in ALL_TOKENS:
                    token = 'statement'
                if token in ('require', 'include', 'extends'):
                    stmt = (stmt.split('(', 1)[1].rsplit(')', 1)[0]
                                .strip(' \t,'))
                return (m.end(), token, stmt)

        def var_token(source, pos):
            """Produce variable token."""
            m = var_match(source, pos)
            return m and (m.end(), 'var', m.group(1).replace(line_join, ''))

        def markup_token(source, pos, twotok=token_start + token_start):
            """Produce markup token."""
            m = markup_match(source, pos)
            return m and (m.end(), 'markup',
                          (m.group().replace(twotok, token_start)
                                    .replace(line_join, '') or None))

        def clean_source(source):
            """Clean leading whitespace for all control tokens."""
            return _clean(r'\1', source.replace('\r\n', '\n'))

        super(Parser, self).__init__(
            lexer_rules=[stmt_token, var_token, markup_token],
            preprocessors=[clean_source])

    def end_continue(self, tokens):
        """If token is ``continue`` prepend it with ``end`` token so
        it simulates a closed block.
        """
        for lineno, token, value in tokens:
            if token == 'continue':
                yield lineno, 'end', None
            yield lineno, token, value

    def parse_iter(self, tokens):
        operands = []
        for lineno, token, value in tokens:
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
                yield lineno, token, (value, vals)
            else:
                yield lineno, token, value
                if token == 'end':
                    break
        if operands:
            yield operands[0][0], 'out', operands


class BlockBuilder(list):

    filters = {'s': 'str', 'e': 'escape'}
    writer_declare = '_b = []; w = _b.append'
    writer_return = "return ''.join(_b)"

    def __init__(self, indent='', lineno=0, nodes=None):
        self.indent = indent
        self.lineno = self.offset = lineno
        self.local_vars = []
        if nodes:
            self.build_block(nodes)

    def __enter__(self):
        self.indent += '    '

    def __exit__(self, exc_type, exc_value, exc_tb):
        assert len(self.indent) >= 4
        self.indent = self.indent[:-4]

    def add(self, lineno, code, token='statement'):
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
        return True

    def build_block(self, nodes):
        for lineno, token, value in nodes:
            self.build_token(lineno, value, token)
        return True

    def build_token(self, lineno, value, token):
        assert token in self.rules, ('No rule to build "%s" token '
                                     'at line %d.' % (token, lineno))
        return any(r(self, lineno, value, token) for r in self.rules[token])

    def compile_code(self, name):
        source = compile('\n'.join(self), name, 'exec', ast.PyCF_ONLY_AST)
        ast.increment_lineno(source, self.offset)
        return compile(source, name, 'exec')

    # all builder rules

    def build_extends(self, lineno, nodes, token):
        assert token == 'render'
        if len(nodes) != 1:
            return
        lineno, token, value = nodes[0]
        if token != 'extends':
            return
        extends, nodes = value
        stmt = 'return _r(' + extends + ', ctx, local_defs, super_defs)'
        self.build_block([n for n in nodes if n[1] in ('def', 'require')])
        return self.add(self.lineno + 1, stmt)

    def build_import(self, lineno, value, token):
        assert token == 'import'
        parts = value[7:].rsplit(None, 2)
        if len(parts) == 3 and parts[1] == 'as':
            if parts[0] in self.local_vars or not isidentifier(parts[0]):
                return self.add(lineno, parts[2] + ' = _i(' + parts[0] + ')')
        return self.add(lineno, value)

    def build_from(self, lineno, value, token):
        assert token == 'from'
        name, tok2, var = value[5:].rsplit(None, 2)
        alias = var
        if tok2 == 'as':
            name, tok2, var = name.rsplit(None, 2)
        assert tok2 == 'import'
        if name in self.local_vars or not isidentifier(name):
            value = "%s = _i(%s).local_defs['%s']" % (alias, name, var)
        return self.add(lineno, value)

    def build_render_single_markup(self, lineno, nodes, token):
        assert token == 'render' and lineno <= 0
        if not nodes:
            return self.add(lineno, "return ''")
        if len(nodes) == 1:
            ln, token, nodes = nodes[0]
            if token == 'out' and len(nodes) == 1:
                ln, token, value = nodes[0]
                if token == 'markup':
                    return self.add(ln, "return %r" % value)

    def build_render(self, lineno, nodes, token):
        assert token == 'render' and lineno <= 0
        self.add(lineno, self.writer_declare)
        self.build_block(nodes)
        return self.add(self.lineno + 1, self.writer_return)

    def build_def_syntax_check(self, lineno, value, token):
        assert token == 'def'
        stmt, nodes = value
        lineno, token, value = nodes[0]
        if token in COMPOUND_TOKENS:
            token = token.rstrip()
            error = ("The compound statement '%s' is not allowed here. "
                     "Add a line before it with %%#ignore.\n\n%s\n"
                     "    %%#ignore\n    %%%s ..." % (token, stmt, token))
            self.add(lineno, stmt)
            with self:
                return self.add(lineno, 'raise SyntaxError(%r)' % error)

    def build_def_single_markup(self, lineno, value, token):
        assert token == 'def'
        stmt, nodes = value
        if len(nodes) > 2:
            return
        if len(nodes) == 2:
            ln, token, nodes = nodes[0]
            if token != 'out' or len(nodes) > 1:
                return
            ln, token, value = nodes[0]
            if token != 'markup':
                return
            value = repr(value)
        else:
            ln, value = lineno, "''"
        def_name = stmt[4:stmt.index('(', 5)]
        defs = def_name.join(["super_defs['", "'] = ", "; ",
                              " = local_defs.setdefault('", "', ", ")"])
        self.add(lineno, stmt)
        with self:
            self.add(ln, "return " + value)
        return self.add(ln + 1, defs)

    def build_def(self, lineno, value, token):
        assert token == 'def'
        stmt, nodes = value
        def_name = stmt[4:stmt.index('(', 5)]
        defs = def_name.join(["super_defs['", "'] = ", "; ",
                              " = local_defs.setdefault('", "', ", ")"])
        self.add(lineno, stmt)
        with self:
            self.add(lineno + 1, self.writer_declare)
            self.build_block(nodes)
            lineno = self.lineno
            self.add(lineno, self.writer_return)
        return self.add(lineno + 1, defs)

    def build_out(self, lineno, nodes, token):
        assert token == 'out'
        for lineno, token, value in nodes:
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
        assert token in COMPOUND_TOKENS
        stmt, nodes = value
        self.add(lineno, stmt)
        with self:
            return self.build_block(nodes)

    def build_require(self, lineno, value, token):
        variables = [v.strip() for v in value.split(',')]
        stmt = ', '.join(variables) + ' = ' + ', '.join(
            ["ctx['" + name + "']" for name in variables])
        self.local_vars.extend(variables)
        return self.add(lineno, stmt)

    def build_end(self, lineno, value, token):
        if self.lineno != lineno:
            self.add(lineno - 1, '')

    rules = {
        'render': [build_extends, build_render_single_markup, build_render],
        'import': [build_import],
        'from': [build_from],
        'require': [build_require],
        'out': [build_out],
        'def': [build_def_syntax_check, build_def_single_markup, build_def],
        'block': [build_compound],
        'continue': [build_compound],
        'end': [build_end],
        'statement': [add],
        '#': [],
    }


class Engine(object):
    """Assemble the template engine."""

    def __init__(self, loader=None, parser=None, template_class=None):
        self.lock = Lock()
        self.templates, self.renders, self.modules = {}, {}, {}
        self.global_vars = {'_r': self.render, '_i': self.import_name}
        self.template_class = template_class or Template
        self.loader = loader or Loader()
        self.parser = parser or Parser()

    def get_template(self, name=None, **kwargs):
        """Return compiled template."""
        if name and kwargs:
            self.remove(name)
        try:
            return self.templates[name]
        except KeyError:
            return self.compile_template(name, **kwargs)

    @lock_acquire
    def remove(self, name):
        """Remove given ``name`` from internal cache."""
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
        nodes = [(-1, 'block', (def_render, [(0, 'render', list(nodes))]))]
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
engine.global_vars.update({'str': unicode, 'escape': cgi.escape})


def get_template(name=None, source=None):
    if source is not None:
        return engine.get_template(name, source=source)
    return engine.get_template(name)


def render_template(template_name=None, source=None, **context):
    return get_template(template_name, source).render(context)


# The WSGI HTTP server

def wsgiref_adapter(host, port):
    from wsgiref.simple_server import make_server
    srv = make_server(host, port, handle_request)
    srv.serve_forever()

WSGI_ADAPTERS = {'wsgiref': wsgiref_adapter}


def run_fiole(server='wsgiref', host=None, port=None, secret_key=None):
    """Run the fiole web server."""
    global COOKIE_SECRET
    COOKIE_SECRET = secret_key or base64.b64encode(os.urandom(32))

    if server not in WSGI_ADAPTERS:
        raise RuntimeError("Server '%s' is not a valid server.  "
                           "Please choose a different server." % server)

    assert REQUEST_RULES, "No route defined"
    host = host or DEFAULT_BIND['host']
    port = int(port or DEFAULT_BIND['port'])
    print('`fiole` starting up (using %s)...\nListening on http://%s:%s...\n'
          'Use Ctrl-C to quit.\n' % (server, host, port))

    try:
        WSGI_ADAPTERS[server](host, port)
    except KeyboardInterrupt:
        print('\nShutting down.  Have a nice day!')
        raise SystemExit(0)


if __name__ == '__main__':
    import optparse
    import sys
    parser = optparse.OptionParser(version=__version__,
                                   usage="%prog [options] package.module:app")
    parser.add_option('-p', '--port', default='127.0.0.1:8080',
                      help='bind to (default: %default)')
    (options, args) = parser.parse_args()
    (host, sep, port) = options.port.rpartition(':')
    if len(args) != 1:
        parser.error('a single positional argument is required')
    DEFAULT_BIND.update(host=host or DEFAULT_BIND['host'], port=int(port))
    (module, sep, target) = args[0].partition(':')
    sys.path[:0] = ['.']
    sys.modules.setdefault('fiole', sys.modules['__main__'])

    # Load and run server application
    __import__(module)
    (getattr(sys.modules[module], target) if target else run_fiole)()
