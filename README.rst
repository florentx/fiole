========
fiole.py
========

``fiole.py`` is a WSGI micro-framework with the following development
constraints:

* Single file, **no external dependency**
* Provide enough features to build a web application with minimal effort
* Embed **a compact template engine**
* Keep the module reasonably small


Main features:

* Regex-based routing
* Methods GET/HEAD/POST/PUT/DELETE
* Error handlers
* File uploads
* Static files
* Fast template engine
* Secure cookies


**Disclaimer:** this framework is intentionally limited.  If you need a robust
and scalable solution, look elsewhere.


Example
=======

::

  from fiole import get, run_fiole

  @get('/')
  def index(request):
      return 'Hello World!'

  run_fiole()

See ``examples/`` for more usages.


Thanks
======

Thank you to Daniel Lindsley (toastdriven) for `itty
<https://github.com/toastdriven/itty#readme>`_, the itty-bitty web framework
which helped me to kick-start the project.

Thank you to Andriy Kornatskyy (akorn) for his blazingly fast and elegant
template library `wheezy.template <http://pythonhosted.org/wheezy.template/>`_:
it is the inspiration for the template engine of ``fiole.py``.

The following projects were also a great source of ideas:

* `Werkzeug <http://werkzeug.pocoo.org/>`_ (``HTTPHeaders`` and
  ``EnvironHeaders`` datastructures)
* `Bottle <http://bottlepy.org/>`_ (embedding a simple template engine)
* `Jinja2 <http://jinja.pocoo.org/>`_ and `Mako
  <http://www.makotemplates.org/>`_ (common template engine syntax and
  features)
