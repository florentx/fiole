import os
import sys

import fiole
from fiole import *

LOADED_EXAMPLE = ['__init__']
EXAMPLES_DIR = os.path.dirname(__file__)
fiole.TEMPLATE_FOLDER = os.path.join(EXAMPLES_DIR, 'templates')


def empty_fiole():
    """Empty the fiole."""
    fiole.REQUEST_RULES[:] = DEFAULT_REQUEST_RULES
    fiole.ERROR_HANDLERS = dict(DEFAULT_ERROR_HANDLERS)
    fiole.engine.global_vars = dict(DEFAULT_GLOBAL_VARS)
    LOADED_EXAMPLE[0] = '__init__'


def set_default_root():
    """Set the route to /, if it is not configured."""
    if fiole.REQUEST_RULES == DEFAULT_REQUEST_RULES:
        @get('/')
        def route_home(request):
            qs = '?' + request.query if request.query else ''
            raise Redirect('/examples' + qs)
    else:
        for (__, re_match, methods, __, __) in fiole.REQUEST_RULES:
            if re_match('/') and 'GET' in methods:
                return
        get('/')(list_routes)


def load_example(name):
    """Empty the fiole, and load a new example by name."""
    path = os.path.join(EXAMPLES_DIR, name + '.py')
    assert os.path.exists(path)
    qualname = 'examples.' + name
    for modname in list(sys.modules):
        if modname.startswith(qualname):
            del sys.modules[modname]
    empty_fiole()
    fiole.run_fiole = lambda **kw: None
    try:
        __import__(qualname)
    finally:
        fiole.run_fiole = run_fiole
    LOADED_EXAMPLE[0] = name
    set_default_root()


@get('/view_routes')
def list_routes(request):
    """List the routes configured."""
    set_default_root()
    return render_template('examples-rules.tmpl',
                           name=LOADED_EXAMPLE[0], rules=fiole.REQUEST_RULES)


@get('/view_source')
def route_example_source(request):
    """View source code of the example."""
    (name,) = request.GET.keys() or LOADED_EXAMPLE
    path = os.path.join(EXAMPLES_DIR, os.path.basename(name + '.py'))
    with open(path) as f:
        return Response(f.read(), content_type='text/plain')


@get('/examples')
def route_examples(request):
    """List all examples, or load the requested example."""
    if request.GET:
        try:
            (name,) = request.GET.keys()
            load_example(name)
        except (ValueError, AssertionError):
            raise Redirect('/examples')
        raise Redirect('/view_routes')
    if not request.headers['Referer']:
        empty_fiole()
    set_default_root()
    examples = []
    for path in os.listdir(EXAMPLES_DIR):
        name, ext = os.path.splitext(path)
        if ext == '.py' and not name.startswith('_'):
            examples.append(name)
    examples.sort()
    return render_template('examples-index.tmpl', names=examples)


@get('/favicon.ico')
def http_favicon(request):
    """Avoid /favicon.ico requests."""
    headers = {'Cache-Control': 'max-age=1200, must-revalidate'}
    return Response('', headers=headers, content_type='image/x-icon')

# Save the default configuration for ``empty_fiole()``
DEFAULT_ERROR_HANDLERS = dict(fiole.ERROR_HANDLERS)
DEFAULT_REQUEST_RULES = list(fiole.REQUEST_RULES)
DEFAULT_GLOBAL_VARS = dict(fiole.engine.global_vars)


@errorhandler(404)
def volatile_not_found(request):
    """Volatile error handler to fix the default root on first NotFound."""
    fiole.ERROR_HANDLERS.pop(404)
    set_default_root()
    raise Redirect('/')


if __name__ == '__main__':
    set_default_root()
    run_fiole()
