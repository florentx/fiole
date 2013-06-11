Developer's notes
=================

Frequently asked questions
--------------------------

.. contents::
   :local:
   :backlinks: top


Another web framework, are you kidding me?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:doc:`Fiole<intro>` is a new challenger in the category of the Python
micro-frameworks.  As you probably know, there are very good competitors
in the market and we don't really need a new one.

Read :doc:`the introduction<intro>` for a quick outline of the
development guidelines for the ``Fiole`` framework.

So, how ``Fiole`` is different or similar to the others?

* `web.py`_ is the first in the series, created in January 2006 by
  Aaron Swartz (aaronsw).  It has no dependency and it supports old versions
  of Python, but it is not compatible with Python 3.  It is a whole package
  and it provides additional features, while ``Fiole`` focuses on the
  essentials.  ``web.py`` does not support the decorator syntax, compared
  with more recent frameworks.

* `itty.py`_ is a single-file micro-framework experiment, released on March
  2009.  It is the first `Sinatra`_-influenced Python framework.  However,
  it does not have public tests, and it does not ship a template engine.

* `Bottle`_ is a micro-web framework born on July 2009.  ``Fiole`` is
  similar to ``Bottle`` because it is a single file, inspired by
  ``itty.py``, with no dependency.  It embeds a template engine, which has
  a syntax close to Bottle's `SimpleTemplate`_.  When it comes to the
  differences, ``Fiole`` template engine is faster, and its source code is
  smaller and follows the PEP 8 guidelines.  On the other side
  ``Bottle`` has more features and it supports plugins.

* `Flask`_ is the successor of `Denied`_, born on 1st April 2010.  It is
  a great framework with `a must-read documentation`_.  ``Flask`` is a
  package which depends on `Werkzeug`_ and `Jinja`_.  In contrast with it,
  ``Fiole`` is a single file without external dependencies and with a lot
  less documentation and less features.  ``Flask`` has many extensions.

To sum up:

* ``Fiole`` is a single file like ``itty.py`` and ``Bottle``
* ``Fiole`` has no dependency, same as ``web.py``, ``itty.py`` and ``Bottle``
* ``Fiole`` embeds a template engine similar to ``web.py`` and ``Bottle``
* ``Fiole`` supports the decorator syntax like ``itty.py``, ``Bottle``
  and ``Flask``
* ``Fiole`` supports signed cookies like ``Flask`` does
* ``Fiole`` source code is PEP8-compliant like ``itty.py`` and ``Flask``
* ``Fiole`` supports Python 3 like ``Bottle``

* ``Fiole`` *does not* have an extensive documentation like ``Flask``
  or ``Bottle``
* ``Fiole`` *does not* provide built-in adapters for every WSGI server
  like ``itty.py`` or ``Bottle``
* ``Fiole`` *does not* provide a plugin mechanism like ``Flask``
  or ``Bottle``

Of course the above comparison is partial and subjective.

.. _web.py: http://www.infoworld.com/d/application-development/pillars-python-webpy-web-framework-169072
.. _itty.py: http://toastdriven.com/blog/2009/mar/07/itty-sinatra-inspired-micro-framework/
.. _Sinatra: http://sinatrarb.com/
.. _Bottle: http://bottlepy.org/
.. _SimpleTemplate: http://bottlepy.org/docs/dev/stpl.html
.. _Werkzeug: http://werkzeug.pocoo.org/
.. _Jinja: http://jinja.pocoo.org/
.. _Denied: http://lucumr.pocoo.org/2010/4/3/april-1st-post-mortem/
.. _Flask: http://flask.pocoo.org/
.. _a must-read documentation: http://flask.pocoo.org/docs/


How much is it extensible?
~~~~~~~~~~~~~~~~~~~~~~~~~~

``Fiole`` is thread-safe and you can configure more than one application (for
complex projects).

``Fiole`` does not provide a built-in facility to install plugins.
However, the components of ``Fiole`` are thought to allow some extensibility.
For example the template engine is configurable through attributes, and all
the components of the template engine can be subclassed easily.

As an alternative, you can use any template engine, such as ``Jinja`` or
``Mako`` instead of the built-in template engine.  There's no specific
integration between ``Fiole`` and the built-in template ``Engine``.

Only the adapter for the ``wsgiref`` server is provided.  You can write your
own adapter for your preferred WSGI server.  There are examples available
in ``Bottle`` or ``itty.py`` source code for example.


How to make my application really fast?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

First, I am not an expert about this topic.
Still, there are various places where you can improve the performance of
your web application.  Some ideas that come to my mind:

* use a reverse proxy (``nginx``, ...)
* delegate serving static files to the proxy
* enable on-the-fly gzip compression on the proxy
* provide the relevant HTTP headers to enable browser caching
* replace the WSGI server with a scalable WSGI server which supports
  concurrency
* add server caching
* use load-balancing
* switch to Pypy


The template engine is already very fast.  Even so, you can achieve a better
performance with small changes:

* disable ``default_filters`` and use the ``|str`` filter only when needed
* replace the ``escape`` filter with a C implementation (e.g. ``Webext``)

However the first thing to do is to benchmark your own application with
realistic data in order to know where is the bottleneck before doing any
random optimization.


I need only the template engine, can you release it?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Indeed, the :doc:`template engine<template>` has some benefits:  it is
compact (~450 lines of code) and it is rather intuitive (basically, it's
Python syntax).  It is derived from the `wheezy.template`_ package `which
is very fast`_.

The template engine can be used to process any kind of text.

The good news is that the template engine is not bound to the web framework.
Currently there's no plan to release it separately because ``Fiole``
is already a very small module and there's nothing wrong using only one of
its two components: the *web framework* or the *template engine*.

.. _wheezy.template: http://wheezytemplate.readthedocs.org/en/latest/
.. _which is very fast:  http://mindref.blogspot.ch/2012/07/python-fastest-template.html


Source code
-----------

The source code is `available on GitHub`_ under the terms and conditions
of the :ref:`BSD license <license>`.  Fork away!

The tests are run against Python 2.7, 3.2, 3.3 and Pypy on the `Travis-CI
platform <http://travis-ci.org/florentx/fiole>`_.

Project on PyPI: https://pypi.python.org/pypi/fiole

.. _available on GitHub: https://github.com/florentx/fiole


Changes
-------

.. include:: ../CHANGES.rst
   :start-line: 3
