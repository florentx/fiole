# -*- coding: utf-8 -*-
from fiole import *


@get('/ct')
def ct(request):
    response = Response('Check your Content-Type headers.',
                        content_type='text/plain')
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
    return u'Works with Unîcødé too!'


# Cookies

@get('/receive')
def receive_cookies(request):
    secure_cookie = request.get_secure_cookie('foo')
    content = '%r\n\n%s' % (request.cookies, secure_cookie)
    response = Response(content, content_type='text/plain')
    return response


@get('/send')
def send_cookie(request):
    response = Response('<a href="/receive">Check your cookies.</a>')
    response.set_cookie('foo', 'bar')
    response.set_cookie('session', 'asdfjlasdfjsdfkjgsdfogd')
    return response


@get('/send_secure')
def send_secure_cookie(request):
    response = Response('<a href="/receive">Check your cookies.</a>')
    response.set_secure_cookie('foo', 'bar')
    return response


@get('/clear')
def clear_cookies(request):
    response = Response('', status=302, headers=[('Location', '/receive')])
    for name in request.cookies:
        response.clear_cookie(name)
    return response


run_fiole(secret_key='MySeCrEtCoOkIe')
