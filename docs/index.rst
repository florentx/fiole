.. Fiole documentation master file, created by
   sphinx-quickstart on Mon May 20 01:24:46 2013.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Fiole's documentation!
======================

Contents:

.. toctree::
   :maxdepth: 2

   intro
   routing
   template
   API <api>
   developer


Indices and tables
==================

* :ref:`genindex`
* :ref:`search`


.. _credits:

Credits
=======

Project created by Florent Xicluna.

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


.. _license:

License
=======

This software is provided under the terms and conditions of the BSD license::

  # Redistribution and use in source and binary forms, with or without
  # modification, are permitted provided that the following conditions are met:
  #
  #   * Redistributions of source code must retain the above copyright
  #     notice, this list of conditions and the following disclaimer.
  #
  #   * Redistributions in binary form must reproduce the above copyright
  #     notice, this list of conditions and the following disclaimer in the
  #     documentation and/or other materials provided with the distribution.
  #
  #   * The names of the contributors may not be used to endorse or
  #     promote products derived from this software without specific
  #     prior written permission.
  #
  # THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT OWNERS AND CONTRIBUTORS "AS IS"
  # AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
  # IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
  # ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNERS OR CONTRIBUTORS BE
  # LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
  # CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
  # SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
  # INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
  # CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
  # ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF
  # THE POSSIBILITY OF SUCH DAMAGE.
