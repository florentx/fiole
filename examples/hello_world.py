from fiole import get, get_template, run_fiole

index_template = get_template(source="""%require(name)
<html>
Hello World!<br><br>
  Hello {{name|e}}<br><br>
%for i in range(len(name)):
  Hello {{name[:i+1]|e}}<br>
%endfor
</html>""")


@get('/')
@get('/(?P<name>\w*)')
def index(request, name='stranger'):
    return index_template.render(name=name)

run_fiole()
