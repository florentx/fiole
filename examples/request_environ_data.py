from fiole import *


@get('/test_get_data')
def index(request):
    try:
        # Should raise an error.
        return 'What? Somehow found a remote user: %s' % request.REMOTE_USER
    except KeyError:
        pass

    return render_template("""\
Remote Addr: {{ request.REMOTE_ADDR|repr|e }}<br>
GET name: {{ request.GET.get('name', 'undefined')|repr|e }}<br>
GET foo: {{ request.GET.get('foo', 'undefined')|repr|e }}
""", request=request)


@get('/simple_post')
def simple_post(request):
    with open('examples/html/simple_post.html', 'r') as f:
        return f.read()


@post('/test_post')
def test_post(request):
    return "'foo' is: %s" % request.POST.get('foo', 'not specified')


@get('/complex_post')
def complex_post(request):
    with open('examples/html/complex_post.html', 'r') as f:
        return f.read()


@post('/test_complex_post')
def test_complex_post(request):
    html = """
    'foo' is: %s<br>
    'bar' is: %s
    """ % (request.POST.get('foo', 'not specified'),
           request.POST.get('bar', 'not specified'))
    return html


run_fiole()
