Changelog
=========

.. currentmodule:: fiole

0.x (unreleased)
~~~~~~~~~~~~~~~~

* Improve documentation.

* Add the Fiole application to the WSGI environment:
  ``environ['fiole.app']``.  (Issue #1)

* Replace the global ``SECRET_KEY`` with a new attribute of
  the Fiole application ``app.secret_key``.

* Replace the helpers ``_create_signed_value`` and ``_decode_signed_value``
  with methods: :meth:`Fiole.encode_signed` and :meth:`Fiole.decode_signed`.
  The method :meth:`Response.create_signed_value` is removed too.

* Remove argument ``secret`` from the ``run_fiole`` function: use
  ``get_app().secret_key = 's3c4e7k3y...'`` instead.

* Rename helper ``html_escape`` to ``escape_html``.

* Refactor the internals of the template engine.


0.2 (2013-05-22)
~~~~~~~~~~~~~~~~

* Initial release.
