# -*- coding: utf-8 -*-
"""Unit tests for ``fiole`` templates."""

import unittest


class TemplateTestCase(unittest.TestCase):
    """Test the compiled templates."""

    def setUp(self):
        from fiole import Engine, Loader
        self.templates = {}
        self.engine = Engine(loader=Loader(templates=self.templates))

    def render(self, ctx, source):
        self.templates['test.html'] = source
        template = self.engine.get_template('test.html')
        self.engine.remove('test.html')
        return template.render(ctx)

    def test_markup(self):
        ctx = {}
        self.assertEqual(self.render(ctx, 'Hello'), 'Hello')

    def test_comment(self):
        self.assertEqual(self.render({}, """\
Hello\\
%# comment
 World"""),
                         'Hello World')
        self.assertEqual(self.render({}, """\
Hello\\
% # comment
 World"""),
                         'Hello World')

    def test_import(self):
        self.assertEqual(self.render({}, """\
% from math import pi
Pi = {{ '%.9f' % pi }}"""),
                         'Pi = 3.141592654')
        self.assertEqual(self.render({}, """\
% import  math \n\
Pi = {{ '%.9f' % math.pi }}"""),
                         'Pi = 3.141592654')
        self.assertEqual(self.render({}, """\
%# import  this \n\
% import  itertools
# {{ 42 | s }} {{ locals()|sorted |s }}"""),
                         """\
# 42 ['_b', 'ctx', 'itertools', 'local_defs', 'super_defs', 'w']""")

    def test_var(self):
        ctx = {'username': 'John'}
        self.assertEqual(self.render(ctx, """\
%require(username)
Welcome, {{username}}!"""), 'Welcome, John!')

    def test_var_extra_space(self):
        ctx = {'username': 'John'}
        self.assertEqual(self.render(ctx, """\
%require( username  , \\
                    )
Welcome, {{
    \tusername\t
}}!"""),
                         'Welcome, John!')

    def test_if(self):
        template = """\
%require(n)
%if n > 0:
    Positive\\
%elif n == 0:
    Zero\\
%else:
    Negative\\
%end
"""
        self.assertEqual(self.render({'n': +1}, template), '    Positive')
        self.assertEqual(self.render({'n': +0}, template), '    Zero')
        self.assertEqual(self.render({'n': -1}, template), '    Negative')

    def test_for(self):
        ctx = {'colors': ['red', 'yellow']}
        self.assertEqual(self.render(ctx, """\
%require(colors)
%for color in colors:
    {{color}}
%end
"""),
                         '    red\n    yellow\n')

    def test_def(self):
        self.assertEqual(self.render({}, """\
%def welcome(name):
Welcome, {{name}}!\\
%end
{{welcome('John')}}"""),
                         'Welcome, John!')

    def test_def_empty(self):
        self.assertEqual(self.render({}, """\
%def title():
%end
{{title()}}."""),
                         '.')

    def test_def_syntax_error_compound(self):
        self.assertRaises(SyntaxError, self.render, {}, """\
%def welcome(name):
%if name:
Welcome, {{name}}!\\
%end
%end
{{welcome('John')}}""")

    def test_def_no_syntax_error(self):
        self.assertEqual(self.render({}, """\
%def welcome(name):
%#ignore
%if name:
Welcome, {{name}}!\\
%end
%end
{{welcome('John')}}"""),
                         'Welcome, John!')

    def test_backslash(self):
        self.assertRaises(SyntaxError, self.render, {}, """\
  %def say_hi(name):
Hi, {{name}}\
  %end
{{ say_hi('Noël')}}""")

    def test_return_early(self):
        template = """\
%require(magic)
    First Line\\
% if magic == 987:
%     return 'Moar Lines'
% elif magic == 42:
%     return
% end
    Second Line\\
"""
        self.assertEqual(self.render({'magic': 27}, template),
                         '    First Line    Second Line')
        self.assertEqual(self.render({'magic': 42}, template),
                         '    First Line')
        self.assertEqual(self.render({'magic': 987}, template), 'Moar Lines')
