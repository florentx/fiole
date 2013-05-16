from fiole import get, run_fiole


@get('/')
def index(request):
    return 'Hello World!'


run_fiole()
