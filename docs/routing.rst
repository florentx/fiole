Routing requests
================

.. currentmodule:: fiole

Decorators
----------

Declare the routes of your application using the Fiole decorators.

Example::

    @route('/about')
    def about(request):
        return "About Fiole sample application"

    @get('/home')
    def home(request):
        return "Sweet"

Both :func:`route` and :func:`get` declare a route for the ``GET`` (and
``HEAD``) methods.
The other decorators are :func:`post`, :func:`put` and :func:`delete`.

The :func:`route` decorator supports an extended syntax to match multiple
methods to the same function::

    @route('/api', methods=('GET', 'HEAD', 'POST'))
    def multi(request):
        return "Received %s %s" % (request.method, request.path)

It is also available as a plain function::

    def say_hi(request):
        return "Hi"

    route('/welcome', methods=('GET', 'HEAD'), callback=say_hi)
    route('/ciao', methods=('GET', 'HEAD'), callback=say_hi)


Dynamic routes
--------------

Two different syntaxes are supported.

**Easy syntax**

The simple syntax for URL pattern is like ``"/hello/<name>"``.
The placeholder matches a non-empty path element (excluding ``"/"``)::

    @get('/')
    @get('/hello/<name>')
    def ciao(request, name='Stranger'):
        return render_template('Hello {{name}}!', name=name)


**Regex syntax**

The advanced syntax is regex-based.  The variables are extracted from the
named groups of the regular expression: ``(?P<name>...)``.
See `Regular Expressions <http://docs.python.org/2/library/re>`_ for the
full syntax.  The unnamed groups are ignored.  The initial ``^``
and the final ``$`` chars should be omitted: they are automatically added
when the route is registered.

The pattern parser switches to the advanced syntax when an extension
notation is detected: ``(?``.

Example::

    @get(r'/api/(?P<action>[^:]+):?(?P<params>.*)')
    def call_api(request, action, params):
        if action == 'view':
            return "Params received {0}".format(params)
        raise NotFound("This action is not supported")


.. _hooks:

Hooks
-----

There's a flexible way to define extensions for ``Fiole``: you can register
hooks which will be executed for each request.  For example you can setup
a database connection before each request, and release the connection after
the request.

A dumb no-op hook looks like::

    app = get_app()

    @app.hooks.append
    def noop_hook(request):
        # acquire the resource
        # ...
        try:
            # pre-process the Request
            # ...
            response = yield
            # post-process the Response
            # ...
            yield response
        finally:
            # release the resource
            pass

This example setup a database connection::

    @app.hooks.append
    def hook_db(request):
        request.db = connect_db()
        try:
            # forward the response unchanged
            yield (yield)
        finally:
            request.db.close()


.. _helpers:

Helpers
-------

Redirect a request::

    @get('/test_redirect')
    def test_redirect(request):
        raise Redirect('/hello')

Return an error page::

    @get('/test_404')
    def test_404(request):
        raise NotFound('Not here, sorry.')

Register a different error page::

    template_404 = get_template("error404.tmpl")

    @errorhandler(404)
    def not_found(request):
        return template_404.render(request)

Send static files::

    get_app().static_folder = "/path/to/public/directory"

    @get('/static/(?P<path>.+)')
    def download(request, path):
        return send_file(request, path)
