from pprint import pformat

from fiole import *


UPLOAD_HTML = """%extends("debug-layout.tmpl")
%def content():
    <form method="post" action="/test_upload?ft=42" \
enctype="multipart/form-data">
      <label>Foo: <input type="text" name="foo" value=""></label><br>
      <label>File:
        <input type="file" name="myfile">
      </label><br>
      <input type="submit" value="Post!">
    </form>
%enddef
"""

engine.global_vars['pretty'] = pformat


@get('/upload')
def upload(request):
    return render_template(source=UPLOAD_HTML, title='Upload', request=request)


@post('/test_upload')
def test_upload(request):
    if getattr(request.POST['myfile'], 'filename', None):
        myfilename = request.POST['myfile'].filename
        myfile_contents = request.POST['myfile'].file.read()
        with open(myfilename, 'w') as uploaded_file:
            uploaded_file.write(myfile_contents)
    return render_template('debug-layout.tmpl',
                           title='Upload result', request=request)

run_fiole()
