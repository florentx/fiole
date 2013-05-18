"""Unit tests for ``fiole`` templates."""

import unittest


class LoaderTestCase(unittest.TestCase):
    """Test the ``DictLoader``."""

    def setUp(self):
        from fiole import Loader
        self.loader = Loader(templates={
            'tmpl1.html': 'x',
            'shared/master.html': 'x'
        })

    def test_list_names(self):
        """Tests list_names."""
        self.assertEqual(self.loader.list_names(), (
            'shared/master.html',
            'tmpl1.html'
        ))

    def test_load_existing(self):
        """Tests load."""
        self.assertEqual(self.loader.load('tmpl1.html'), 'x')

    def test_load_not_found(self):
        """Tests load if the name is not found."""
        self.assertRaises(Exception, self.loader.load, 'tmpl-x.html')


class CleanSourceTestCase(unittest.TestCase):
    """Test the ``clean_source`` preprocessor."""

    def setUp(self):
        from fiole import Parser
        self.clean_source = Parser().preprocessors[0]

    def test_new_line(self):
        """Replace windows new line with linux new line."""
        self.assertEqual(self.clean_source('a\r\nb'), 'a\nb')

    def test_clean_leading_whitespace(self):
        """Remove leading whitespace before %<stmt>, e.g. %if, %for, etc."""
        from fiole import ALL_TOKENS
        self.assertIn('#', ALL_TOKENS)
        for tok in ALL_TOKENS:
            self.assertEqual(self.clean_source('  %' + tok), '%' + tok)
            self.assertEqual(self.clean_source('\n  %' + tok), '\n%' + tok)
            self.assertEqual(self.clean_source('a\n  %' + tok), 'a\n%' + tok)

        # Clean leading whitespace before % b tokens.
        self.assertEqual(self.clean_source('a\n\n   %b'), 'a\n\n%b')
        self.assertEqual(self.clean_source('a\n %b'), 'a\n%b')
        self.assertEqual(self.clean_source('a\n%b'), 'a\n%b')
        self.assertEqual(self.clean_source('a%  b'), 'a%  b')
        self.assertEqual(self.clean_source('  %b'), '%b')

    def test_leave_leading_whitespace(self):
        """Leave leading whitespace before {{<var>}} tokens."""
        self.assertEqual(self.clean_source('a\n\n  {{var}}'), 'a\n\n  {{var}}')
        self.assertEqual(self.clean_source('a\n {{var}}'), 'a\n {{var}}')
        self.assertEqual(self.clean_source('a\n{{var}}'), 'a\n{{var}}')
        self.assertEqual(self.clean_source('a{{var}}'), 'a{{var}}')
        self.assertEqual(self.clean_source('  {{var}}'), '  {{var}}')

    def test_ignore(self):
        """Ignore double %."""
        self.assertEqual(self.clean_source('a\n  %%b'), 'a\n  %%b')
        self.assertEqual(self.clean_source('  %%b'), '  %%b')


class LexerTestCase(unittest.TestCase):
    """Test the default lexer."""

    def setUp(self):
        from fiole import Engine
        self.engine = Engine()

    def tokenize(self, source):
        return self.engine.parser.tokenize(source)

    def test_stmt_token(self):
        """Test statement token."""
        tokens = self.tokenize('%require(title, users)\n')
        self.assertEqual(tokens, [(1, 'require', ['title', 'users'])])
        tokens = self.tokenize('% require (title,users)\n')
        self.assertEqual(tokens, [(1, 'require', ['title', 'users'])])

    def test_comment_token(self):
        """Test statement token."""
        tokens = self.tokenize('%#ignore\\\n%end\n')
        self.assertEqual(tokens, [(1, '#', '#ignore%end')])
        tokens = self.tokenize('% ## ignore\\' '\n%end\n')
        self.assertEqual(tokens, [(1, '#', '## ignore%end')])

    def test_var_token(self):
        """Test variable token."""
        tokens = self.tokenize('{{user.name}}')
        self.assertEqual(tokens, [(1, 'var', 'user.name')])
        tokens = self.tokenize('{{user.pref[i].fmt() }}')
        self.assertEqual(tokens, [(1, 'var', 'user.pref[i].fmt()')])
        tokens = self.tokenize('{{  user. name  }}')
        self.assertEqual(tokens, [(1, 'var', 'user. name')])
        tokens = self.tokenize('{{  user.pref[i].fmt( ) }}')
        self.assertEqual(tokens, [(1, 'var', 'user.pref[i].fmt( )')])

    def test_var_token_filter(self):
        """Test variable token filter."""
        tokens = self.tokenize('{{ user.age|s }}')
        self.assertEqual(tokens, [(1, 'var', 'user.age|s')])
        tokens = self.tokenize('{{user.age|s|h }}')
        self.assertEqual(tokens, [(1, 'var', 'user.age|s|h')])
        tokens = self.tokenize('{{user}}| ')
        self.assertEqual(tokens, [(1, 'var', 'user'), (1, 'markup', '| ')])
        tokens = self.tokenize('{{ user.age | s}}|')
        self.assertEqual(tokens,
                         [(1, 'var', 'user.age | s'), (1, 'markup', '|')])
        tokens = self.tokenize('{{user .age}}||s')
        self.assertEqual(tokens,
                         [(1, 'var', 'user .age'), (1, 'markup', '||s')])

    def test_markup_token(self):
        """Test markup token."""
        tokens = self.tokenize(' test ')
        self.assertEqual(tokens, [(1, 'markup', ' test ')])
        tokens = self.tokenize('x%n')
        self.assertEqual(tokens, [(1, 'markup', 'x%n')])
        tokens = self.tokenize('x{{n}}')
        self.assertEqual(tokens, [(1, 'markup', 'x'), (1, 'var', 'n')])

    def test_markup_token_escape(self):
        """Test markup token with escape."""
        tokens = self.tokenize('support%%acme.org')
        self.assertEqual(tokens, [(1, 'markup', 'support%acme.org')])
        tokens = self.tokenize('support %%acme.org')
        self.assertEqual(tokens, [(1, 'markup', 'support %acme.org')])
        tokens = self.tokenize('support% %acme.org')
        self.assertEqual(tokens, [(1, 'markup', 'support% %acme.org')])


class ParserTestCase(unittest.TestCase):
    """Test the default parser."""

    def setUp(self):
        from fiole import Engine
        self.engine = Engine()

    def parse(self, source):
        return list(self.engine.parser.parse_iter(
            self.engine.parser.end_continue(
                self.engine.parser.tokenize(source))))

    def test_require(self):
        """Test parse_require."""
        nodes = self.parse('%require(title, users)\n')
        self.assertEqual(nodes, [(1, 'require', ['title', 'users'])])
        nodes = self.parse('  % require( title , users )\n')
        self.assertEqual(nodes, [(1, 'require', ['title', 'users'])])

    def test_extends(self):
        """Test parse_extends."""
        nodes = self.parse('%extends("shared/master.html")\n')
        self.assertEqual(nodes, [(1, 'extends', ('"shared/master.html"', []))])
        nodes = self.parse(' % extends ( "shared/master.html")\n')
        self.assertEqual(nodes, [(1, 'extends', ('"shared/master.html"', []))])

    def test_include(self):
        """Test parse_include."""
        nodes = self.parse('%include("shared/scripts.html")\n')
        self.assertEqual(
            nodes, [(1, 'out', [
                (1, 'include', '"shared/scripts.html"')
            ])])

    def test_markup(self):
        """Test parse_markup."""
        nodes = self.parse("""\n Welcome, {{name}}!\n""")
        self.assertEqual(
            nodes, [(1, 'out', [
                (1, 'markup', '\n Welcome, '),
                (2, 'var', 'name'),
                (2, 'markup', '!\n')
            ])])
        nodes = self.parse("""\n Welcome, {{ name }}!\n   """)
        self.assertEqual(
            nodes, [(1, 'out', [
                (1, 'markup', '\n Welcome, '),
                (2, 'var', 'name'),
                (2, 'markup', '!\n   ')
            ])])

    def test_var(self):
        """Test parse_markup."""
        nodes = self.parse("""{{name|h}}!""")
        self.assertEqual(
            nodes, [(1, 'out', [
                (1, 'var', 'name|h'),
                (1, 'markup', '!')
            ])])
        nodes = self.parse("""{{name|s|h}}!""")
        self.assertEqual(
            nodes, [(1, 'out', [
                (1, 'var', 'name|s|h'),
                (1, 'markup', '!')
            ])])
        nodes = self.parse("""{{ name|h }}!""")
        self.assertEqual(
            nodes, [(1, 'out', [
                (1, 'var', 'name|h'),
                (1, 'markup', '!')
            ])])
        nodes = self.parse("""{{ name | s | h }}|""")
        self.assertEqual(
            nodes, [(1, 'out', [
                (1, 'var', 'name | s | h'),
                (1, 'markup', '|')
            ])])

    def test_import(self):
        """Test import statement."""
        nodes = self.parse(' %import "views/helpers.tmpl" as  helpers ')
        self.assertEqual(nodes, [
            (1, 'import', 'import "views/helpers.tmpl" as  helpers ')])
        nodes = self.parse("  %import 'views/helpers.tmpl' as helpers ")
        self.assertEqual(nodes, [
            (1, 'import', "import 'views/helpers.tmpl' as helpers ")])
        nodes = self.parse('  %from "views/helpers.html" import colorize ')
        self.assertEqual(nodes, [
            (1, 'from', 'from "views/helpers.html" import colorize ')])
        nodes = self.parse('  %import this  ')
        self.assertEqual(nodes, [(1, 'import', 'import this  ')])
        nodes = self.parse('  %import this  # abc')
        self.assertEqual(nodes, [(1, 'import', 'import this  # abc')])
        nodes = self.parse('  %from math import pi')
        self.assertEqual(nodes, [(1, 'from', 'from math import pi')])
        nodes = self.parse('  %from   math  import  pi')
        self.assertEqual(nodes, [(1, 'from', 'from math  import  pi')])
