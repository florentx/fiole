# -*- coding: utf-8 -*-
"""Unit tests for ``fiole`` templates with inheritance
(extends, include, import).
"""

import unittest


class MultiTemplateTestCase(unittest.TestCase):
    """Test the compiled templates."""

    def setUp(self):
        from fiole import Engine, Loader
        self.templates = {}
        self.engine = Engine(loader=Loader(templates=self.templates))

    def render(self, name, ctx):
        template = self.engine.get_template(name)
        self.engine.remove('test.html')
        return template.render(ctx)

    def test_extends(self):
        self.templates.update({
            'master.html': """\
%def say_hi(name):
    Hello, {{name}}!
%end
{{say_hi('John')}}""",

            'tmpl.html': """\
%extends('master.html')
%def say_hi(name):
    Hi, {{name}}!
%end
"""
        })
        self.assertEqual(self.render('tmpl.html', {}), '    Hi, John!\n')
        self.assertEqual(self.render('master.html', {}), '    Hello, John!\n')
        self.assertEqual(self.render('tmpl.html', {}), '    Hi, John!\n')
        self.assertEqual(self.render('master.html', {}), '    Hello, John!\n')

    def test_super(self):
        self.templates.update({
            'master.html': """\
%def say_hi(name):
    Hello, {{name}}!\\
%end
{{say_hi('John')}}""",
            'tmpl.html': """\
%extends('master.html')
%def say_hi(name):
    {{super_defs['say_hi'](name)}}!!\\
%end
"""
        })
        self.assertEqual(self.render('tmpl.html', {}),
                         '        Hello, John!!!')

    def test_include(self):
        self.templates.update({
            'footer.html': """\
%require(name)
Thanks, {{name}}""",
            'tmpl.html': """\
Welcome to my site.
%include('footer.html')
"""
        })
        ctx = {'name': 'John'}
        self.assertEqual(self.render('tmpl.html', ctx), """\
Welcome to my site.
Thanks, John""")
        self.assertEqual(self.render('footer.html', ctx), 'Thanks, John')

    def test_import(self):
        self.templates.update({
            'helpers.html': """\
%def say_hi(name):
Hi, {{name}}\\
%end""",
            'tmpl.html': """\
%import 'helpers.html' as helpers
{{helpers.say_hi('John')}}"""
        })
        self.assertEqual(self.render('tmpl.html', {}), "Hi, John")

    def test_import_dynamic(self):
        self.templates.update({
            'helpers.html': """\
%def say_hi(name):
Hi, {{name}}\\
%end""",
            'tmpl.html': """\
%require(helpers_impl)
%import helpers_impl as helpers
{{helpers.say_hi('John')}}"""
        })
        self.assertEqual(self.render('tmpl.html',
                                     {'helpers_impl': 'helpers.html'}),
                         "Hi, John")

    def test_from_import(self):
        self.templates.update({
            'helpers.html': """\
%def say_hi(name):
Hi, {{name}}\\
%end""",
            'tmpl.html': """\
%from 'helpers.html' import say_hi
{{say_hi('John')}}"""
        })
        self.assertEqual(self.render('tmpl.html', {}), "Hi, John")

    def test_from_import_dynamic(self):
        self.templates.update({
            'helpers.html': """\
%def say_hi(name):
Hi, {{name}}\\
%end""",
            'tmpl.html': """\
%require(helpers_impl)
%from helpers_impl import say_hi
{{say_hi('John')}}"""
        })
        self.assertEqual(self.render('tmpl.html',
                                     {'helpers_impl': 'helpers.html'}),
                         "Hi, John")

    def test_from_import_as(self):
        self.templates.update({
            'share/helpers.html': """\
%def say_hi(name):
Hi, {{name}}\\
%end""",
            'tmpl.html': """\
%from 'share/helpers.html' import say_hi as hi
{{hi('John')}}"""
        })
        self.assertEqual(self.render('tmpl.html', {}), "Hi, John")

    def test_import_syntax_error(self):
        self.templates.update({
            'helpers.html': """\
%def say_hi(name):
Hi, {{name}}\
%end""",
            'tmpl.html': """\
%import 'helpers.html' as helpers
{{helpers.say_hi('John')}}"""
        })
        self.assertRaises(SyntaxError, self.render, 'tmpl.html', {})

    def test_import_dynamic_syntax_error(self):
        self.templates.update({
            'helpers.html': """\
%def say_hi(name):
Hi, {{name}}\
%end""",
            'tmpl.html': """\
%require(helpers_impl)
%import helpers_impl as helpers
{{helpers.say_hi('John')}}"""
        })
        self.assertRaises(SyntaxError, self.render, 'tmpl.html',
                          {'helpers_impl': 'helpers.html'})

    def test_from_import_syntax_error(self):
        self.templates.update({
            'helpers.html': """\
%def say_hi(name):
Hi, {{name}}\
%end""",
            'tmpl.html': """\
%from 'helpers.html' import say_hi
{{say_hi('John')}}"""
        })
        self.assertRaises(SyntaxError, self.render, 'tmpl.html', {})

    def test_from_import_dynamic_syntax_error(self):
        self.templates.update({
            'helpers.html': """\
%def say_hi(name):
Hi, {{name}}\
%end""",
            'tmpl.html': """\
%require(helpers_impl)
%from helpers_impl import say_hi
{{say_hi('John')}}"""
        })
        self.assertRaises(SyntaxError, self.render, 'tmpl.html',
                          {'helpers_impl': 'helpers.html'})

    def test_from_import_as_syntax_error(self):
        self.templates.update({
            'share/helpers.html': """\
% def say_hi( name ):
Hi, {{name}}\
% end""",
            'tmpl.html': """\
%  from  "share/helpers.html" import  say_hi  as  hi
{{hi('John')}}"""
        })
        self.assertRaises(SyntaxError, self.render, 'tmpl.html', {})
