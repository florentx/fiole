.. currentmodule:: fiole

Template engine
===============

*Parts of this page are converted from the wheezy.template documentation.
Thank you to the author.* (:ref:`akorn<credits>`)

``Fiole`` comes with a decent template engine.  It supports the usual
features of well known engines (*Mako*, *Jinja2*).
The engine is derived from the wonderful `wheezy.template`_ package.
It retains the same design goals:

* intuitive, use the full power of Python
* inherit your templates (``%extends``, ``%include`` and ``%import``)
* stay *blazingly* `fast
  <http://mindref.blogspot.ch/2012/07/python-fastest-template.html>`__.


In a nutshell, the syntax looks as simple as `Bottle SimpleTemplate`_:

* ``{{ ... }}`` executes the enclosed :ref:`expression<template_expressions>`
  and inserts the result.  The expression must return a Unicode or
  ASCII string.
* Use the ``|s`` filter to cast random Python objects to Unicode.
* Use the ``|e`` filter to convert any of ``& < > " '`` to HTML-safe
  sequences.
* A single percent ``%`` at the beginning of the line identifies a
  :ref:`template directive<template_directives>` or
  :ref:`Python code<template_python_code>`.
  (except if it is repeated: ``%%``)
* Spaces and indentation around the ``%`` special char are ignored.
* A backslash ``\`` at the end of a line will skip the line ending.


Simple template:

.. code-block:: mako

    %require(user, items)
    Welcome, {{user.name}}!
    %if items:
        %for i in items:
            {{i.name}}: {{i.price|s}}.
        %endfor
    %else:
        No item found.
    %endif


.. contents::
   :local:
   :depth: 2
   :backlinks: top


.. _Bottle SimpleTemplate: http://bottlepy.org/docs/dev/stpl.html
.. _wheezy.template: http://wheezytemplate.readthedocs.org/en/latest/


.. _template_expressions:

Template loading
----------------

This is a basic example for a route mapped to a template::

    @get('/')
    @get('/hello/<name>')
    def hello(request, name=None):
        return render_template(
            source='Hello {{party.title() if party else "stranger"}}!', party=name)

In this case the template is not cached.  It is built again for each request.

In order to activate the cache, the string template should be assigned to a
name.  The previous example becomes::

    # Preload the cache
    get_template('hello_tpl',
                 source="""Hello {{party.title() if party else "stranger"}}!""",
                 require=['party'])

    @get('/')
    @get('/hello/<name>')
    def hello(request, name=None):
        return render_template('hello_tpl', party=name)


Templates can be saved to files in the ``./templates/`` folder of the project.
Then they are loaded by filename and cached in memory::

    @get('/')
    def index(request):
        return render_template('hello.tmpl', party='World')



Inline expressions
------------------

Variables
~~~~~~~~~

The variables which need to be extracted from the context are listed in the
``require`` directive.  These names become visible to the
end of the template scope (a template is like a Python function).
The application passes variables to the template via context:

.. code-block:: mako

    %require(var1, var2)

    {{ var1 }} ... {{ var2 }}

For string templates, you can declare the variables using the ``require``
keyword argument::

    >>> hello_tmpl = get_template(source='Hello {{ party.capitalize() }}!', require=['party'])
    >>> hello_tmpl.render(party='WORLD')
    u'Hello World!'
    >>> hello_tmpl.render({'party': 'world'})
    u'Hello World!'

This declaration is omitted when rendering the string directly::

    >>> render_template(source='Hello {{party}}!', party='World')
    u'Hello World!'
    >>> #
    >>> render_template(source='Hello {{ party.capitalize() }}!', party='world')
    u'Hello World!'

Variable syntax is not limited to a single name access.  You are able to use
the full power of Python to access items in dictionary, attributes,
function calls, etc...

The expression must return a Unicode string, or use the ``|s`` filter
when appropriate::

    >>> render_template(source='# {{ a }} - {{ b }} = {{ a - b }}', a=56, b=14)
    Traceback (most recent call last):
      File "<stdin>", line 1, in <module>
      File "./fiole.py", line 1076, in render_template
        return get_template(template_name, source, context).render(context)
      File "./fiole.py", line 1057, in render
        return self.render_template(ctx or kwargs, {}, {})
      File "<string>", line 3, in render
    TypeError: sequence item 1: expected str instance, int found
    >>> #
    >>> render_template(source='# {{ a|s }} - {{ b|s }} = {{ a - b|s }}', a=56, b=14)
    u'# 56 - 14 = 42'


Filters
~~~~~~~

Variables can be formatted by filters.  Filters are separated from the variable
by the ``|`` symbol.  Filter syntax:

.. code-block:: mako

    {{ variable_name|filter1|filter2 }}

The filters are applied from left to right so above syntax is equivalent to
the following call:

.. code-block:: mako

    {{ filter2(filter1(variable_name)) }}

Two default filters are provided:

* the ``|s`` filter cast random Python objects to Unicode.
* the ``|e`` filter convert any of ``& < > " '`` to HTML-safe sequences.


A simple example:

.. code-block:: mako

    {{ user.age|s }}

Assuming the age property of user is integer we apply string filter.


You can define and use custom filters too.  Here is an example how to switch
to a different implementation for the html escape filter::

    try:
        from webext import escape_html
        engine.global_vars['escape'] = escape_html
    except ImportError:
        pass

It tries to import an optimized version of html escape from the `Webext`_
package and assign it to the ``escape`` global variable, which is aliased
as ``e`` filter.  The built-in ``escape`` is pure Python.

An example which demonstrates the standard ``|e`` filter::

    >>> render_template('This: {{ data | e }}', data='"Hello small\' <i>World!<i>" ... & farther')
    u'This: &quot;Hello small&#x27; &lt;i&gt;World!&lt;i&gt;&quot; ... &amp; farther'


You are able to use engine :data:`Engine.global_vars` dictionary in order
to simplify your template access to some commonly used variables.


.. _`Webext`: https://pypi.python.org/pypi/Webext

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


Inheritance
~~~~~~~~~~~

Template inheritance (``%extends``) allows to build a master template that
contains common layout of your site and defines areas that child templates
can override.


Master Template
^^^^^^^^^^^^^^^

Master template is used to provide common layout of your site.  Let define
master template (filename ``shared/master.html``):

.. code-block:: mako

    <html>
      <head>
        <title>
        %def title():
        %enddef
        {{title()}} - My Site</title>
      </head>
      <body>
        <div id="content">
          %def content():
          %enddef
          {{content()}}
        </div>
        <div id="footer">
          %def footer():
          &copy; Copyright 2014 by Him.
          %enddef
          {{footer()}}
        </div>
      </body>
    </html>

In this example, the ``%def`` tags define python functions (substitution
areas).  These functions are inserted into specific places (right after
definition).  These places become placeholders for child templates.
The ``%footer`` placeholder defines default content while ``%title`` and
``%content`` are just empty.

Child Template
^^^^^^^^^^^^^^

Child templates are used to extend master templates via placeholders defined:

.. code-block:: mako

    %extends("shared/master.html")

    %def title():
      Welcome
    %enddef

    %def content():
      <h1>Home</h1>
      <p>
        Welcome to My Site!
      </p>
    %enddef

In this example, the ``%title`` and ``%content`` placeholders are overriden
by the child template.


Include
~~~~~~~

The include is useful to insert a template content just in place of call:

.. code-block:: mako

    %include("shared/snippet/script.html")


Import
~~~~~~

The import is used to reuse some code stored in other files.  So you are
able to import all functions defined by that template:

.. code-block:: mako

    %import "shared/forms.html" as forms

    {{ forms.textbox('username') }}

or just a certain name:

.. code-block:: mako

    %from "shared/forms.html" import textbox

    {{ textbox(name='username') }}

Once imported you use these names as variables in the template.



.. _template_python_code:

Python code
-----------

Any line starting with a single ``%`` and which is not recognized as a
directive is actual Python code.  Its content is copied to the generated source
code.


Line Statements
~~~~~~~~~~~~~~~

The ``%import`` and ``%from`` lines can be either directives or Python
commands, depending on their arguments.

In addition to the special ``%def``, all kinds of Python blocks are supported.
The indentation is not significant, blocks must be ended explicitly.

* ``%for``, ``%if``, ``%elif``, ``%else``, ``%while``: loops and conditionals
* ``%try``, ``%except``, ``%else``, ``%finally``: exception handlers
* ``%end`` identifies the end of the inner block.  It is recommended to use the
  specific ``%endfor``, ``%endif``, ``%endwhile`` or ``%endtry`` directive,
  even if this rule is not strictly enforced
* for completeness ``%class``/``%endclass`` and ``%with``/``%endwith`` are also
  supported

The empty ``%return`` directive triggers an early return in the template.  The
code execution is stopped and the generated content is returned.


Here is a simple example:

.. code-block:: mako

    %require(items)
    %if items:
      %for i in items:
        {{i.name}}: {{i.price|s}}.
      %endfor
    %else:
      No items found.
    %endif


Line Comments
~~~~~~~~~~~~~

Only single line comments are supported.

The ``%#`` directive introduces a one-line comment.  Comments are removed
before the template is compiled.

.. code-block:: mako

    %# TODO:


Line Join
~~~~~~~~~

In case you need to continue a long line without breaking it with new line
during rendering use line join (``\``):

.. code-block:: mako

    %if menu_name == active:
      <li class='active'> \
    %else:
      <li> \
    %endif


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


These features are not supported (among others):

* code blocks: as an alternative, prepend a ``%`` on each line
* multi-line comments: prepend ``%#`` on each line
