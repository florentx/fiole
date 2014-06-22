Fiole API
=========

.. module:: fiole


Decorators
----------

.. autofunction:: route(url, methods=('GET', 'HEAD'), callback=None, status=200)
.. autofunction:: get(url)
.. autofunction:: post(url)
.. autofunction:: put(url)
.. autofunction:: delete(url)
.. autofunction:: errorhandler(code)


Helpers
-------

.. autofunction:: send_file(request, filename, root=None, content_type=None, buffer_size=65536)
.. autofunction:: get_template
.. autofunction:: render_template

.. data:: engine

   Default instance of the Template :class:`Engine`.

.. data:: default_app

   Default :class:`Fiole` application.

.. autofunction:: get_app
.. autofunction:: run_wsgiref
.. autofunction:: run_fiole(app=default_app, server=run_wsgiref, host=None, port=None)


WSGI application
----------------

.. autoclass:: Fiole

   .. automethod:: push
   .. automethod:: pop
   .. attribute:: debug

      Enable debugging: don't catch internal server errors (500) and
      unhandled exceptions.  (default: *False*)

   .. attribute:: secret_key

      Secret key used to sign secure cookies.  (default: *unset*)

   .. attribute:: static_folder

      Directory where static files are located.  (default: *./static*)

   .. attribute:: hooks

      List of :ref:`hooks` which are registered for this application.

   .. automethod:: handle_request
   .. automethod:: handle_error
   .. automethod:: find_matching_url
   .. automethod:: route
   .. automethod:: get
   .. automethod:: post
   .. automethod:: put
   .. automethod:: delete
   .. automethod:: errorhandler
   .. automethod:: encode_signed
   .. automethod:: decode_signed
   .. automethod:: send_file

.. autoclass:: Request

   Environment variables are also accessible through :class:`Request`
   attributes.

   .. attribute:: environ

      Dictionary of environment variables

   .. attribute:: path

      Path of the request, decoded and with ``/`` appended.

   .. attribute:: method

      HTTP method (GET, POST, PUT, ...).

   .. attribute:: query

      Read ``QUERY_STRING`` from the environment.

   .. attribute:: script_name

      Read ``SCRIPT_NAME`` from the environment.

   .. attribute:: host_url

      Build host URL.

   .. attribute:: headers

      An instance of :class:`EnvironHeaders` which wraps HTTP headers.

   .. attribute:: content_length

      Header ``"Content-Length"`` of the request as integer or ``0``.

   .. attribute:: accept

      Header ``"Accept"`` of the request.
      Return an :class:`Accept` instance.

   .. attribute:: accept_charset

      Header ``"Accept-Charset"`` of the request.
      Return an :class:`Accept` instance.

   .. attribute:: accept_encoding

      Header ``"Accept-Encoding"`` of the request.
      Return an :class:`Accept` instance.

   .. attribute:: accept_language

      Header ``"Accept-Language"`` of the request.
      Return an :class:`Accept` instance.

   .. autoattribute:: GET
   .. autoattribute:: POST
   .. autoattribute:: PUT
   .. autoattribute:: body
   .. autoattribute:: cookies

   .. automethod:: get_cookie
   .. automethod:: get_secure_cookie
   .. automethod:: get_url

.. autoclass:: Response

   .. autoattribute:: charset
   .. attribute:: status

      Status code of the response as integer (default: *200*)

   .. attribute:: headers

      Response headers as :class:`HTTPHeaders`.

   .. automethod:: set_cookie
   .. automethod:: clear_cookie
   .. automethod:: set_secure_cookie
   .. automethod:: send

.. autoclass:: HTTPHeaders

   An instance of :class:`HTTPHeaders` is an iterable.  It yields
   tuples ``(header_name, value)``.  Additionally it provides
   a dict-like interface to access or change individual headers.

   .. automethod:: __getitem__

      Access the header by name.  This method is case-insensitive
      and the first matching header is returned.  It returns
      :const:`None` if the header does not exist.

   .. automethod:: get
   .. automethod:: get_all
   .. automethod:: add
   .. automethod:: set
   .. automethod:: setdefault
   .. automethod:: to_list
   .. automethod:: keys
   .. automethod:: values
   .. automethod:: items

.. autoclass:: EnvironHeaders

   .. automethod:: __getitem__

      Access the header by name.  This method is case-insensitive
      and returns :const:`None` if the header does not exist.

   .. automethod:: get
   .. automethod:: get_all
   .. automethod:: keys
   .. automethod:: values
   .. automethod:: items

.. autoclass:: Accept

   .. automethod:: __contains__
   .. automethod:: quality
   .. automethod:: best_match

.. autoexception:: HTTPError
.. autoexception:: BadRequest
.. autoexception:: Forbidden
.. autoexception:: NotFound
.. autoexception:: MethodNotAllowed
.. autoexception:: Redirect
.. autoexception:: InternalServerError


Template engine
---------------

.. autoclass:: Engine

   .. attribute:: global_vars

      This mapping contains additional globals which are injected in the
      generated source.  Two special globals are used internally and must
      not be modified: ``_r`` and ``_i``.  The functions ``str`` and
      ``escape`` (alias ``e``) are also added here.  They are used as filters.
      They can be replaced by C extensions for performance (see `Webext`_).
      Any object can be added to this registry for usage in the templates,
      either as function or filter.

   .. attribute:: default_filters

      The list of filters which are applied to all template expressions
      ``{{ ... }}``.  Set to ``None`` to remove all default filters, for
      performance.  (default: *['str']*)

   .. automethod:: clear
   .. automethod:: get_template
   .. automethod:: remove(name)
   .. automethod:: import_name
   ..
      render
      compile_template
      compile_import
      load_and_parse

.. autoclass:: Template()

   .. autoattribute:: name

      Name of the template (it can be :const:`None`).

   .. method:: render(context)
               render(**context)

      Render the template with these arguments (either a dictionary
      or keyword arguments).

.. autoclass:: Loader
   :members:

   .. attribute:: template_folder

      Directory where template files are located.  (default: *./templates*)

.. autoclass:: Lexer
   :members:

.. autoclass:: Parser

   .. automethod:: tokenize
   .. automethod:: end_continue
   .. automethod:: parse_iter

.. autoclass:: BlockBuilder

   .. autoattribute:: filters

      A mapping of declared template filters (aliases of globals).  This
      mapping can be extended.  The globals can be extended too, see
      :data:`Engine.global_vars`.

   .. attribute:: rules

      A mapping of ``tokens`` with list of methods, to generate the source
      code.

   .. automethod:: add
   .. automethod:: compile_code

.. _Webext: https://pypi.python.org/pypi/Webext
