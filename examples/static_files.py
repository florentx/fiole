import os.path

from fiole import *

MY_ROOT = os.path.join(os.path.dirname(__file__), 'media')


@get('/')
def index(request):
    return '<img src="media/fiole.png">'


# To serve static files, simply setup a standard @get method.  You should
# capture the filename/path and use the ``send_file`` handler to
# serve up the file.  If your media root is different than where
# your ``fiole.py`` lives, manually setup your root directory as well.
@get('/media/(?P<filename>.+)')
def my_media(request, filename):
    return send_file(request, filename, root=MY_ROOT)


# Another example:
@get('/simple/')
def simple(request):
    return """
<html>
  <head>
    <title>Simple CSS</title>
    <link rel="stylesheet" type="text/css" href="/simple_media/default.css">
  </head>
  <body>
    <h1>Simple CSS is Simple!</h1>
    <p>Simple reset here.</p>
  </body>
</html>
"""


# By default, the ``send_file`` will try to guess the correct content
# type. If needed, you can enforce a content type by using the
# ``content_type`` kwarg (i.e. ``content_type='image/jpg'`` on a
# directory of user uploaded images).
@get('/simple_media/(?P<filename>.+)')
def simple_media(request, filename):
    return send_file(request, filename, root=MY_ROOT)


run_fiole()
