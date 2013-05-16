from fiole import *


@errorhandler(500)
def my_great_500(exception):
    html_output = """
    <html>
        <head>
            <title>Application Error! OH NOES!</title>
        </head>

        <body>
            <h1>OH NOES!</h1>

            <p>Yep, you broke it.</p>

            <p>Exception: %s</p>
        </body>
    </html>
    """ % exception
    return Response(html_output, status=500)


@get('/hello')
def hello(request):
    return 'Hello errors!'


@get('/test_404')
def test_404(request):
    raise NotFound('Not here, sorry.')
    return 'This should never happen.'


@get('/test_500')
def test_500(request):
    raise AppError('Oops.')
    return 'This should never happen either.'


@get('/test_other')
def test_other(request):
    raise RuntimeError('Oops.')
    return 'This should never happen either either.'


@get('/test_403')
def test_403(request):
    raise Forbidden('No soup for you!')
    return 'This should never happen either either either.'


@get('/test_redirect')
def test_redirect(request):
    raise Redirect('/hello')


run_fiole()
