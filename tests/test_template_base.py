"""Unit tests for template engine bricks:

 * ``fiole.Lexer``
 * ``fiole.Parser``
 * ``fiole.BlockBuilder``
 * ``fiole.Engine``
"""

import unittest


class LexerTestCase(unittest.TestCase):
    """Test the ``Lexer``."""

    def test_tokenize(self):
        """Test with simple rules."""
        import re
        from fiole import Lexer

        def word_token(source, pos):
            m = re.compile(r'\w+').match(source, pos)
            return m and (m.end(), 'w', m.group())

        def blank_token(source, pos):
            m = re.compile(r'\s+').match(source, pos)
            return m and (m.end(), 'b', m.group())

        lexer = Lexer([word_token, blank_token])
        self.assertEqual(lexer.tokenize('hello\n world'),
                         [(1, 'w', 'hello'),
                          (1, 'b', '\n '),
                          (2, 'w', 'world')])

    def test_trivial(self):
        """Empty rules and source."""
        from fiole import Lexer
        lexer = Lexer([])
        self.assertEqual(lexer.tokenize(''), [])

    def test_raises_error(self):
        """If there is no match it raises SyntaxError."""
        from fiole import Lexer
        lexer = Lexer([])
        self.assertRaises(SyntaxError, lexer.tokenize, 'test')


class ParserTestCase(unittest.TestCase):
    """Test the ``Parser``."""

    def setUp(self):
        from fiole import Parser
        self.parser = Parser()

    def parse(self, tokens):
        return list(self.parser.parse_iter(self.parser.end_continue(tokens)))

    def test_end_continue(self):
        """Ensure end nodes are inserted before continue tokens."""
        tokens = [
            (1, 'a', 11),
            (2, 'continue', 12),
            (3, 'c', 13),
            (4, 'continue', 14),
            (5, 'c', 15),
        ]
        nodes = list(self.parser.end_continue(tokens))
        self.assertEqual(len(nodes), 7)
        self.assertEqual(nodes[1], (2, 'end', None))
        self.assertEqual(nodes[2], (2, 'continue', 12))
        self.assertEqual(nodes[4], (4, 'end', None))
        self.assertEqual(nodes[5], (4, 'continue', 14))

    def test_parse_unchanged(self):
        """No parser tokens defined the result is unchanged input."""
        tokens = [
            (1, 'a', 11),
            (2, 'b', 12),
            (3, 'c', 13),
            (4, 'b', 14),
            (5, 'c', 15),
        ]
        self.assertEqual(self.parse(tokens), tokens)

    def test_out_tokens(self):
        """Tokens from ``out_tokens`` are combined together
        into a single node.
        """
        # OUT_TOKENS = ['markup', 'var', 'include']
        tokens = [
            (1, 'include', 11),
            (2, 'var', 12),
            (3, 'c', 13),
            (4, 'var', 14),
            (5, 'c', 15),
        ]
        nodes = self.parse(tokens)
        self.assertEqual(len(nodes), 4)
        self.assertEqual(nodes[0], (1, 'out',
                                    [(1, 'include', 11), (2, 'var', 12)]))
        self.assertEqual(nodes[2], (4, 'out', [(4, 'var', 14)]))

        tokens = [
            (1, 'a', 11),
            (2, 'var', 12),
            (3, 'markup', 13),
            (4, 'var', 14),
            (5, 'markup', 15),
        ]
        nodes = self.parse(tokens)
        self.assertEqual(len(nodes), 2)
        self.assertEqual(nodes[1], (2, 'out', [
            (2, 'var', 12),
            (3, 'markup', 13),
            (4, 'var', 14),
            (5, 'markup', 15)]))

    def test_compound(self):
        # COMPOUND_TOKENS = ['extends', 'def', 'block', 'continue']
        tokens = [
            (1, 'a', 11),
            (2, 'extends', 12),
            (3, 'end', 13),
            (4, 'def', 14),
            (5, 'end', 15),
        ]
        nodes = self.parse(tokens)
        self.assertEqual(len(nodes), 3)
        self.assertEqual(nodes[1], (2, 'extends', (12, [(3, 'end', 13)])))
        self.assertEqual(nodes[2], (4, 'def', (14, [(5, 'end', 15)])))


class BlockBuilderTestCase(unittest.TestCase):
    """Test the ``BlockBuilder`` blocks."""

    def setUp(self):
        from fiole import BlockBuilder
        self.builder = BlockBuilder(lineno=0)

    def test_start_end_block(self):
        """Test start_block and end_block."""
        self.assertEqual(self.builder.indent, '')
        with self.builder:
            self.assertEqual(self.builder.indent, ' ' * 4)
        self.assertEqual(self.builder.indent, '')

    def test_inconsistence(self):
        """Test add a line with wrong lineno."""
        self.assertRaises(Exception, self.builder.add, -1, '')

    def test_unknown_token(self):
        """Test raises error if token is unknown."""
        self.assertRaises(Exception, self.builder.build_token, 1, 'x', None)


class BlockBuilderAddSameLineTestCase(unittest.TestCase):
    """Test the ``BlockBuilder.add`` to the same line."""

    def setUp(self):
        from fiole import BlockBuilder
        self.builder = BlockBuilder(indent='    ', lineno=1)

    def test_code_empty(self):
        self.builder[:] = ['']
        self.builder.add(1, '')
        self.assertEqual(self.builder, [''])

    def test_line_empty(self):
        self.builder[:] = ['']
        self.builder.add(1, 'pass')
        self.assertEqual(self.builder, ['    pass'])

    def test_line_ends_colon(self):
        self.builder[:] = ['def title():']
        self.builder.add(1, 'return ""')
        self.assertEqual(self.builder, ['def title():return ""'])

    def test_continue_same_line(self):
        self.builder[:] = ['pass']
        self.builder.add(1, 'pass')
        self.assertEqual(self.builder, ['pass; pass'])


class BlockBuilderAddNextLineTestCase(unittest.TestCase):
    """Test the ``BlockBuilder.add`` to add a new line."""

    def setUp(self):
        from fiole import BlockBuilder
        self.builder = BlockBuilder(indent='    ', lineno=0)

    def test_code_empty(self):
        self.builder.add(1, 'pass')
        self.builder.add(2, '')
        self.assertEqual(self.builder, ['    pass', ''])

    def test_pad(self):
        self.builder.add(1, 'pass')
        self.builder.add(3, 'pass')
        self.assertEqual(self.builder, ['    pass', '', '    pass'])


class EngineTestCase(unittest.TestCase):
    """Test the ``Engine``."""

    def setUp(self):
        from fiole import Engine
        self.engine = Engine()

    def test_template_not_found(self):
        """Raises."""
        self.assertRaises(Exception, self.engine.get_template, 'x')

    def test_import_not_found(self):
        """Raises."""
        self.assertRaises(Exception, self.engine.import_name, 'x')

    def test_remove_unknown_name(self):
        """Invalidate name that is not known to engine."""
        self.assertNotIn('x', self.engine.templates)
        self.assertNotIn('x', self.engine.renders)
        self.assertNotIn('x', self.engine.modules)
        self.engine.remove('x')

    def test_remove_name(self):
        """Invalidate name that is known to engine."""
        self.engine.templates['x'] = 'x'
        self.engine.renders['x'] = 'x'
        self.engine.modules['x'] = 'x'
        self.assertIn('x', self.engine.templates)
        self.assertIn('x', self.engine.renders)
        self.assertIn('x', self.engine.modules)
        self.engine.remove('x')
        self.assertNotIn('x', self.engine.templates)
        self.assertNotIn('x', self.engine.renders)
        self.assertNotIn('x', self.engine.modules)
