# -*- coding: utf-8 -*-
from fiole import *

u = str if (str is not bytes) else lambda s: s.decode('utf-8')

XML_DOCUMENT="""\
<?xml version="1.0" encoding="UTF-8"?>
<root><info>Check your Content-Type headers.</info>
<俄语>данные</俄语></root>
"""


@get('/ct_default')
def ct(request):
    response = Response(XML_DOCUMENT)
    return response


@get('/ct_plain')
def ct(request):
    response = Response(XML_DOCUMENT, content_type='text/plain')
    return response


@get('/ct_xml')
def ct(request):
    response = Response(XML_DOCUMENT, content_type='application/xml')
    return response


@get('/headers')
def test_headers(request):
    headers = [
        ('X-Powered-By', 'fiole'),
        ('Set-Cookie', 'username=paul')
    ]
    response = Response('Check your headers.', headers=headers)
    return response


@get('/redirected')
def index(request):
    return 'You got redirected!'


@get('/test_redirect')
def test_redirect(request):
    raise Redirect('/redirected')


@get('/unicode')
def unicode(request):
    return u('Works with Unîcødé too!')


# Cookies

@get('/receive')
def receive_cookies(request):
    unsecure_cookie = request.get_cookie('foo')
    secure_cookie = request.get_secure_cookie('foo')
    content = '%r\n\nunsecure: %s\nsecure: %s' % (
        request.cookies, unsecure_cookie, secure_cookie)
    response = Response(content, content_type='text/plain')
    return response


@get('/send')
def send_cookie(request):
    response = Response('<a href="/receive">Check your cookies.</a>')
    response.set_cookie('foo', u('bär'))
    response.set_cookie('session', 'asdfjlasdfjsdfkjgsdfogd')
    return response


@get('/send_secure')
def send_secure_cookie(request):
    response = Response('<a href="/receive">Check your cookies.</a>')
    response.set_secure_cookie('foo', u('bär'))
    return response


@get('/clear')
def clear_cookies(request):
    response = Response('', status=302, headers=[('Location', '/receive')])
    for name in request.cookies:
        response.clear_cookie(name)
    return response


if __name__ == '__main__':
    # Run
    get_app().secret_key = 'MySeCrEtCoOkIe'
    run_fiole()
