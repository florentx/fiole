"""Unit tests for ``fiole`` templates."""

import unittest


class BuilderTestCase(unittest.TestCase):
    """Test the code generators."""

    def setUp(self):
        from fiole import Engine
        self.engine = Engine()

    def build_source(self, source):
        from fiole import BlockBuilder
        nodes = list(self.engine.parser.parse_iter(
            self.engine.parser.end_continue(
                self.engine.parser.tokenize(source))))
        builder = BlockBuilder(lineno=0)
        builder.build_block(nodes)
        return '\n'.join(builder)

    def build_render(self, source):
        from fiole import BlockBuilder
        nodes = list(self.engine.parser.parse_iter(
            self.engine.parser.end_continue(
                self.engine.parser.tokenize(source))))
        source = BlockBuilder(lineno=-2)
        source.add(-1, 'def render(ctx, local_defs, super_defs):')
        with source:
            source.build_token(0, nodes, 'render')
        return '\n'.join(source)

    def build_extends(self, name, source):
        nodes = list(self.engine.parser.parse(
            self.engine.parser.tokenize(source)))
        return self.engine.parser.build_extends(name, nodes)

    def test_markup(self):
        self.assertEqual(self.build_source('Hello'), "w('Hello')")
        self.assertEqual(self.build_source('Hello%'), "w('Hello%')")
        self.assertEqual(self.build_source('Hello%o'), "w('Hello%o')")

    def test_comment(self):
        self.assertEqual(self.build_source("""\
Hello\\
%# comment
 World"""),
                         """\
w('Hello')

w(' World')""")

    def test_comment_extra_space(self):
        self.assertEqual(self.build_source("""\
Hello\\
% ## comment
 World"""),
                         """\
w('Hello')

w(' World')""")

    def test_require(self):
        self.assertEqual(self.build_source("""\
%require(title, username)
{{username}}"""),
                         """\
title = ctx['title']; username = ctx['username']
w(username)""")

    def test_require_extra_space(self):
        # with space, newlines and extra comma
        self.assertEqual(self.build_source("""\
%require(title, username,)
{{

    username}}; {{ }}; {{ }}."""),
                         """\
title = ctx['title']; username = ctx['username']
w(username)

w('; '); w('; '); w('.')""")

    def test_require_duplicate(self):
        self.assertEqual(self.build_source("""\
%require(title, username)
% require ( title, username )
{{username}}"""),
                         """\
title = ctx['title']; username = ctx['username']

w(username)""")
        self.assertEqual(self.build_source("""\
%require(username)
% require ( title, username )
{{username}}"""),
                         """\
username = ctx['username']
title = ctx['title']
w(username)""")

    def test_out(self):
        """Test build_out."""
        self.assertEqual(self.build_source('Welcome, {{username}}!'),
                         "w('Welcome, '); w(username); w('!')")
        self.assertEqual(self.build_source("""\

<i>
    {{username}}
</i>"""),
                         """\
w('\\n<i>\\n    ')

w(username); w('\\n</i>')""")

    def test_out_extra_space(self):
        """Test build_out with extra space."""

        self.assertEqual(self.build_source('Welcome, {{   username  }}!'),
                         "w('Welcome, '); w(username); w('!')")
        self.assertEqual(self.build_source("""\

<i>
    {{  username}}
</i>"""),
                         """\
w('\\n<i>\\n    ')

w(username); w('\\n</i>')""")

    def test_if(self):
        """Test if elif else statements."""
        self.assertEqual(self.build_source("""\
%if n > 0:
    Positive
%elif n == 0:
    Zero
%else:
    Negative
%end
"""),
                         """\
if n > 0:
    w('    Positive\\n')
elif n == 0:
    w('    Zero\\n')
else:
    w('    Negative\\n')""")

    def test_if_extra_space(self):
        """Test if elif else statements with extra space."""
        self.assertEqual(self.build_source("""\
% if n > 0:
    Positive
%  elif n == 0:
    Zero
%  else:
    Negative
% end
"""),
                         """\
if n > 0:
    w('    Positive\\n')
elif n == 0:
    w('    Zero\\n')
else:
    w('    Negative\\n')""")

    def test_for(self):
        self.assertEqual(self.build_source("""\
%for color in colors:
    {{color}}
%end
"""),
                         """\
for color in colors:
    w('    '); w(color); w('\\n')""")

    def test_for_extra_space(self):
        self.assertEqual(self.build_source("""\
% for color in colors :
    {{color }}
%end
"""),
                         """\
for color in colors :
    w('    '); w(color); w('\\n')""")

    def test_def(self):
        """Test def statement."""
        self.assertEqual(self.build_source("""\
    %def link(url, text):
        <a href="{{url}}">{{text}}</a>
        %#ignore
    %end
    Please {{link('/en/signin', 'sign in')}}.
"""),
                         """\
def link(url, text):
    _b = []; w = _b.append; \
w('        <a href="'); w(url); w('">'); w(text); w('</a>\\n')
    return ''.join(_b)
super_defs['link'] = link; link = local_defs.setdefault('link', link)
w('    Please '); w(link('/en/signin', 'sign in')); w('.\\n')""")

    def test_def_empty(self):
        """Test def statement."""
        self.assertEqual(self.build_source("""\
%def title():
%end
{{title()}}."""),
                         """\
def title():return ''
super_defs['title'] = title; title = local_defs.setdefault('title', title)
w(title()); w('.')""")

    def test_def_extra_space(self):
        """Test def statement with extra space."""
        self.assertEqual(self.build_source("""\
    % def link(url, text):
        <a href="{{url}}">{{text}}</a>
        % ##ignore
    % end
    Please {{ link( '/en/signin', 'sign in' )}}.
"""),
                         """\
def link(url, text):
    _b = []; w = _b.append; \
w('        <a href="'); w(url); w('">'); w(text); w('</a>\\n')
    return ''.join(_b)
super_defs['link'] = link; link = local_defs.setdefault('link', link)
w('    Please '); w(link( '/en/signin', 'sign in' )); w('.\\n')""")

    def test_render(self):
        """Test build_render."""
        self.assertEqual(self.build_render("Hello"),
                         "def render(ctx, local_defs, super_defs):\n"
                         "\n    return 'Hello'")

    def test_extends(self):
        """Test build_extends."""
        self.assertEqual(self.build_render("""%extends("base.html")\n"""),
                         """\
def render(ctx, local_defs, super_defs):
    return _r("base.html", ctx, local_defs, super_defs)""")
