Overview
========

.. currentmodule:: fiole

``fiole.py`` is a WSGI micro-framework with the following development
constraints:

* Single file, **no external dependency**
* Provide enough features to build a web application with minimal effort
* Embed **a compact template engine**
* Keep the module reasonably small


Main features:

* :doc:`Routing <routing>`
* :doc:`Methods GET/HEAD/POST/PUT/DELETE <routing>`
* :ref:`Error handlers <helpers>`
* File uploads (:data:`Request.POST`)
* :ref:`Static files <helpers>`
* :doc:`Fast template engine <template>`
* Secure cookies (:func:`Request.get_cookie`, :func:`Response.set_cookie`, ...)


**Disclaimer:** this framework is intentionally limited.  If you need a robust
and scalable solution, look elsewhere.


Link to the PyPI page: https://pypi.python.org/pypi/fiole

Tested against: Python 2.7, PyPy 2.0 and Python >= 3.2


Quickstart
----------

Either download the single file :download:`fiole.py<../fiole.py>` and save it in your
project directory, or ``pip install fiole``, preferably in a ``virtualenv``.

Create an application and save it with name ``hello.py``:

::

  from fiole import get, run_fiole


  @get('/')
  def index(request):
      return 'Hello World!'

  run_fiole()


Then run this example (default port 8080) with:

.. code-block:: bash

  python hello.py


or (on port 4000 for example):

.. code-block:: bash

  python fiole.py -p 4000 hello
  # (or)
  python -m fiole -p 4000 hello


Next steps
----------

`Clone the examples <https://github.com/florentx/fiole>`_ and run the demo:

.. code-block:: bash

  git clone git://github.com/florentx/fiole.git fiole_git
  cd fiole_git/
  python fiole.py examples

Read the documentation about :doc:`routing` and :doc:`template`.

Some features are not yet covered in the documentation:

* sending and receiving cookies
* adding custom HTTP headers
* stacking multiple applications
* serving through a third-party WSGI server (gevent, ...)


Look at the :doc:`api` for some crispy details.

Read the documentation of `Flask <http://flask.pocoo.org/docs/>`_ and
`Bottle <http://bottlepy.org/docs/dev/>`_ for more information about
web development in general.
