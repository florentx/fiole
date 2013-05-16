import json
import xml.etree.ElementTree as etree

from fiole import *


@get('/json')
def send_json(request):
    values = {'foo': 'bar', 'moof': 123}
    return Response(json.dumps(values), content_type='application/json')


@get('/xml')
def send_xml(request):
    xml = etree.Element('doc')
    etree.SubElement(xml, 'foo', value='bar')
    etree.SubElement(xml, 'moof', value='123')
    return Response(etree.tostring(xml), content_type='application/xml')


@get('/get/(?P<name>\w+)')
def test_get(request, name=', world'):
    return 'Hello %s!' % name


@post('/post')
def test_post(request):
    return "'foo' is: %s" % request.POST.get('foo', 'not specified')


@put('/put')
def test_put(request):
    return "'foo' is: %s" % request.PUT.get('foo', 'not specified')


@delete('/delete')
def test_delete(request):
    return 'Method received was %s.' % request.method


run_fiole()
