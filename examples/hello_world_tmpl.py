from fiole import get, get_template, render_template, run_fiole


@get('/')
@get('/<name>')
def index(request, name='stranger'):
    return render_template("""\
<html>
Hello World!<br><br>
  Hello {{name|e}}<br><br>
%for i in range(len(name)):
  Hello {{name[:i+1]|e}}<br>
%endfor
</html>""", name=name)


# Alternative (pre-load the template)
#
# Note: in this case the declaration ``%require(name)`` is needed,
#   or an iterable is passed to keyword argument ``require`` of
#   the ``get_template`` function.

index_template = get_template(source="""%require(name)
<html>
Hello World!<br><br>
  Hello {{name|e}}<br><br>
%for i in range(len(name)):
  Hello {{name[:i+1]|e}}<br>
%endfor
</html>""")


@get('/hello/<name>')
def hello(request, name='stranger'):
    return index_template.render(name=name)


run_fiole()
