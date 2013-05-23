.. currentmodule:: fiole

Template engine
===============

``Fiole`` comes with a decent template engine.  It supports the usual features
of well known engines (*Mako*, *Jinja2*).
The engine is derived from the wonderful `wheezy.template`_ package:  it is
optimized for performance.

The basic syntax is similar to `Bottle SimpleTemplate`_:

* ``{{ ... }}`` executes the enclosed :ref:`expression<template_expressions>`
  and inserts the result.  The expression must return a Unicode or
  ASCII string.
* Use the ``|s`` filter to cast any object to Unicode.
* Use the ``|e`` filter to convert any of ``& < > " '`` to HTML-safe
  sequences.
* A single percent ``%`` at the beginning of the line identifies a
  :ref:`template directive<template_directives>` or
  :ref:`Python code<template_python_code>`.
  (except if it is repeated: ``%%``)
* Spaces and indentation around the ``%`` special char are ignored.
* A backslash ``\`` at the end of a line will skip the line ending.


.. _Bottle SimpleTemplate: http://bottlepy.org/docs/dev/stpl.html
.. _wheezy.template: http://wheezytemplate.readthedocs.org/en/latest/


.. _template_expressions:

Inline expressions
------------------

This is a basic example::

    @get('/')
    def index(request):
        return render_template(source='Hello {{party}}!', party='World')

And there are other ways to use the API::

    >>> render_template(source='Hello {{party}}!', party='World')
    u'Hello World!'
    >>> render_template(source='Hello {{ party.capitalize() }}!', party='world')
    u'Hello World!'
    >>> hello_tmpl = get_template(source='Hello {{ party.capitalize() }}!', require=['party'])
    >>> hello_tmpl.render(party='WORLD')
    u'Hello World!'
    >>> hello_tmpl.render({'party': 'world'})
    u'Hello World!'

The content of the expression is evaluated as Python code.
It must return a Unicode string, or use the ``|s`` filter when appropriate::

    >>> render_template(source='# {{ a|s }} - {{ b|s }} = {{ a - b|s }}', a=56, b=14)
    u'# 56 - 14 = 42'

The standard ``|e`` filter will encode special HTML chars::

    >>> render_template('This: {{ data | e }}', data='"Hello small\' <i>World!<i>" ... & farther')
    u'This: &quot;Hello small&#x27; &lt;i&gt;World!&lt;i&gt;&quot; ... &amp; farther'


Note: templates can be saved to files in the ``./templates`` folder of
the project.  Then they are loaded by filename (and cached)::

    @get('/')
    def index(request):
        return render_template('hello.tmpl', party='World')


.. _template_directives:

Directives
----------

Any line starting with a single ``%`` contains either a template directive
or Python code.
Following directives are supported:

* ``%extends("layout.tmpl")``: Tell which master template should be extended
  to generate the current document.  This should be the first line.
* ``%require(firstname, lastname)``: Declare the variables which are expected
  when rendering the template.
* ``%include("footer.html")``: Render the template and insert the output
  just here.
* ``%import "widgets.tmpl" as widgets``: Import reusable helpers from another
  template.
* ``%from "toolbox.tmpl" import popup``: Import a function from the other
  template.
* ``%def``: Define a Python function (used for inheritance: ``%extends``
  or ``%import``).
* ``%end`` or ``%enddef``: End the Python function definition.


.. _template_python_code:

Python code
-----------

Any line starting with a single ``%`` and which is not recognized as a
directive is actual Python code.  Its content is copied to the generated source
code.

The ``%import`` and ``%from`` lines can be either directives or Python
commands, depending on their arguments.

In addition to the special ``%def``, all kinds of Python blocks are supported.
The indentation is not significant, blocks must be ended explicitly:

* ``%for``, ``%if/elif/else``, ``%while``, ``%with``, ``%try/except/else/finally``:
  loops, conditionals, context manager and exception handler
* ``%end`` identifies the end of the inner block.  It is recommended to use the
  specific ``%endfor``, ``%endif``, ... directive, even if there's no strict
  rule enforced.
* for completeness ``%class`` and ``%endclass`` are also supported, but they
  are probably useless.

The empty ``%return`` directive triggers an early return in the template.  The
code execution is stopped and the generated content is returned.


The ``%#`` directive introduces a one-line comment.  Comments are removed
before the template is compiled.


.. _template_restrictions:

Restrictions
------------

The line after the ``%def`` directive must not enter a new block (``%for``,
``%if``, etc...).  A workaround is to insert an empty comment line
before opening the block.

The variables used in the template should be declared, either with
a ``%require`` directive (recommended for templates loaded from the
filesystem), or passed as keyword argument ``(require=["nav", "body"])``
when preparing the template (recommended for string templates).
When using the :func:`render_template` function with a ``(source="...")``
keyword argument, the declaration ``%require`` is automatically generated
based on the names of the other keyword arguments passed to the function.

The HTML escaping cannot be activated globally.  Each string which is
potentially unsafe should be filtered with ``|e``.

The output of inline expressions must be Unicode or ASCII only.  Use the
filter ``|s`` to convert any object to Unicode.

Not supported (among others):

* code blocks: as an alternative, prepend a ``%`` on each line
* multi-line comments
