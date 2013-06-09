# -*- coding: utf-8 -*-
"""Unit tests for ``fiole`` template helpers."""

import unittest

from fiole import engine, get_template, render_template


class TemplateHelperTestCase(unittest.TestCase):
    """Test the template helpers: get_template, render_template."""

    def setUp(self):
        engine.templates, engine.renders, engine.modules = {}, {}, {}
    tearDown = setUp

    def test_get_template(self):
        template = get_template(source='Hello')
        self.assertEqual(template.render(), 'Hello')
        self.assertFalse(engine.templates)
        self.assertFalse(engine.renders)
        self.assertFalse(engine.modules)

    def test_render_template(self):
        self.assertEqual(render_template(source='Hello'), 'Hello')
        self.assertFalse(engine.templates)
        self.assertFalse(engine.renders)
        self.assertFalse(engine.modules)

    def test_require_no_directive(self):
        tmpl = "Welcome, {{username}}!"
        result = 'Welcome, John!'
        ctx = {'username': 'John'}

        template = get_template(source=tmpl, require=['username'])
        self.assertEqual(template.render(ctx), result)
        self.assertEqual(template.render(**ctx), result)
        self.assertEqual(template.render(ctx, dummy=42), result)
        self.assertEqual(template.render({}, **ctx), result)
        self.assertEqual(template.render(dummy=42, **ctx), result)
        self.assertEqual(template.render(username=42), 'Welcome, 42!')

        self.assertRaises(TypeError, template.render, 'John')
        self.assertRaises(KeyError, template.render)
        self.assertRaises(KeyError, template.render, dummy='42')
        self.assertRaises(KeyError, template.render, {'abc': 'abc'})

        template = get_template(source=tmpl)
        self.assertRaises(NameError, template.render)
        self.assertRaises(NameError, template.render, ctx)
        self.assertRaises(NameError, template.render, **ctx)

    def test_require_directive(self):
        tmpl = "%require(username)\nWelcome, {{username}}!"
        result = 'Welcome, John!'
        ctx = {'username': 'John'}

        template = get_template(source=tmpl)
        self.assertEqual(template.render(ctx), result)
        self.assertEqual(template.render(**ctx), result)

        template = get_template(source=tmpl, require=['username'])
        self.assertEqual(template.render(ctx), result)
        self.assertEqual(template.render(**ctx), result)
        self.assertEqual(template.render(ctx, dummy=42), result)
        self.assertEqual(template.render({}, **ctx), result)
        self.assertEqual(template.render(dummy=42, **ctx), result)
        self.assertEqual(template.render(username=42), 'Welcome, 42!')

        self.assertRaises(TypeError, template.render, 'John')
        self.assertRaises(KeyError, template.render)
        self.assertRaises(KeyError, template.render, dummy='42')
        self.assertRaises(KeyError, template.render, {'abc': 'abc'})

        template = get_template(source=tmpl, require=['dummy'])
        self.assertRaises(KeyError, template.render, ctx)
        self.assertRaises(KeyError, template.render, **ctx)
        self.assertEqual(template.render(ctx, dummy=42), result)
        self.assertEqual(template.render(dummy=42, **ctx), result)

    def test_render_template_empty(self):
        master_template = get_template('master', source="")
        tmpl = '%extends("master")\n'

        self.assertEqual(master_template.render(), '')
        self.assertEqual(render_template(source=''), '')
        self.assertEqual(render_template(source=tmpl), '')
        self.assertEqual(get_template(source=tmpl).render(), '')

    def test_render_template_require(self):
        tmpl = "Welcome, {{username}}!"
        result = 'Welcome, John!'
        ctx = {'username': 'John'}

        self.assertEqual(render_template(source=tmpl, **ctx), result)
        self.assertEqual(render_template(source=tmpl, dummy=42, **ctx), result)

        self.assertRaises(Exception, render_template)
        self.assertRaises(NameError, render_template, source=tmpl)
        self.assertRaises(NameError, render_template, source=tmpl, dummy=42)

        tmpl = "%require(username)\nWelcome, {{username}}!"
        self.assertEqual(render_template(source=tmpl, **ctx), result)
        self.assertEqual(render_template(source=tmpl, dummy=42, **ctx), result)

        self.assertRaises(KeyError, render_template, source=tmpl)
        self.assertRaises(KeyError, render_template, source=tmpl, dummy=42)

    def test_render_template_extends(self):
        get_template(
            'master',
            source="%def hello():\n%end\n{{ hello() }}{{ name }}!",
            require=['name'])
        tmpl = '%extends("master")\n%def hello():\nWelcome, \\\n%end'
        result = 'Welcome, John!'

        self.assertEqual(render_template(source=tmpl, name='John'), result)
        self.assertEqual(get_template(source=tmpl).render(name='John'), result)

        template = get_template(source=tmpl, require=['name'])
        self.assertEqual(template.render(name='John'), result)
