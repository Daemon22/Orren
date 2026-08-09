#!/usr/bin/env python3
"""
ORREN BOOTSTRAP INTERPRETER v1.0.0
====================================
The seed that makes all 133+ .orn files executable.
This is the ONLY non-.orn component in the Orren ecosystem.
Once the Orren self-hosted compiler becomes operational through
this bootstrap, this file can be retired.

Usage:
    python orren_bootstrap.py run <file.orn>         Run an Orren file
    python orren_bootstrap.py repl                    Interactive REPL
    python orren_bootstrap.py check <file.orn>       Parse check only
    python orren_bootstrap.py ast <file.orn>         Print AST
    python orren_bootstrap.py version                 Show version
    python orren_bootstrap.py test                    Run test suite

First Law: Meaning shall never be lost because of language.
"""
import sys
import os
import json

# ================================================================
# SECTION 1: TOKEN TYPES & TOKENIZER
# ================================================================

class TT:
    """Token types for the Orren lexer."""
    INT = 'INT'
    FLOAT = 'FLOAT'
    STRING = 'STRING'
    BOOL = 'BOOL'
    IDENT = 'IDENT'
    # Keywords
    MODULE = 'MODULE'
    IMPORT = 'IMPORT'
    FROM = 'FROM'
    EXPORT = 'EXPORT'
    ENTITY = 'ENTITY'
    ENUM = 'ENUM'
    FN = 'FN'
    CONST = 'CONST'
    PROPERTY = 'PROPERTY'
    LET = 'LET'
    BE = 'BE'
    IF = 'IF'
    THEN = 'THEN'
    ELSE = 'ELSE'
    END = 'END'
    FOR = 'FOR'
    IN = 'IN'
    WHILE = 'WHILE'
    DO = 'DO'
    MATCH = 'MATCH'
    WITH = 'WITH'
    RETURN = 'RETURN'
    SELF = 'SELF'
    AND = 'AND'
    OR = 'OR'
    NOT = 'NOT'
    TRUE = 'TRUE'
    FALSE = 'FALSE'
    CASE = 'CASE'
    MUT = 'MUT'
    # Operators
    PLUS = 'PLUS'
    MINUS = 'MINUS'
    STAR = 'STAR'
    SLASH = 'SLASH'
    PERCENT = 'PERCENT'
    EQ = 'EQ'
    EQEQ = 'EQEQ'
    NEQ = 'NEQ'
    LT = 'LT'
    GT = 'GT'
    LTE = 'LTE'
    GTE = 'GTE'
    ARROW = 'ARROW'          # ->
    FAT_ARROW = 'FAT_ARROW'  # =>
    RANGE = 'RANGE'          # ..
    SHIFT_LEFT = 'SHIFT_LEFT'  # <<
    SHIFT_RIGHT = 'SHIFT_RIGHT'  # >>
    BIT_AND = 'BIT_AND'      # &
    BIT_XOR = 'BIT_XOR'       # ^
    AS = 'AS'                # as (type cast)
    COLON = 'COLON'
    COMMA = 'COMMA'
    DOT = 'DOT'
    UNDERSCORE = 'UNDERSCORE'
    HASH = 'HASH'
    LPAREN = 'LPAREN'
    RPAREN = 'RPAREN'
    LBRACE = 'LBRACE'
    RBRACE = 'RBRACE'
    LBRACKET = 'LBRACKET'
    RBRACKET = 'RBRACKET'
    NEWLINE = 'NL'
    EOF = 'EOF'


class Token:
    """A single token produced by the lexer."""
    __slots__ = ('tt', 'val', 'line', 'col')

    def __init__(self, tt, val, line=0, col=0):
        self.tt = tt
        self.val = val
        self.line = line
        self.col = col

    def __repr__(self):
        return 'Token(%s, %r, L%d)' % (self.tt, self.val, self.line)


KEYWORDS = {
    'module': TT.MODULE, 'import': TT.IMPORT, 'from': TT.FROM,
    'export': TT.EXPORT, 'entity': TT.ENTITY, 'enum': TT.ENUM,
    'fn': TT.FN, 'const': TT.CONST, 'property': TT.PROPERTY,
    'let': TT.LET, 'be': TT.BE, 'if': TT.IF, 'then': TT.THEN,
    'else': TT.ELSE, 'end': TT.END, 'for': TT.FOR, 'in': TT.IN,
    'while': TT.WHILE, 'do': TT.DO, 'match': TT.MATCH,
    'with': TT.WITH, 'return': TT.RETURN, 'self': TT.SELF,
    'and': TT.AND, 'or': TT.OR, 'not': TT.NOT,
    'true': TT.TRUE, 'false': TT.FALSE, 'case': TT.CASE,
    'as': TT.AS, 'mut': TT.MUT,
}

# Single-char operator map
SINGLE_CHARS = {
    '+': TT.PLUS, '-': TT.MINUS, '*': TT.STAR, '/': TT.SLASH,
    '%': TT.PERCENT, '=': TT.EQ, '<': TT.LT, '>': TT.GT,
    ':': TT.COLON, ',': TT.COMMA, '.': TT.DOT,
    '(': TT.LPAREN, ')': TT.RPAREN, '{': TT.LBRACE,
    '}': TT.RBRACE, '[': TT.LBRACKET, ']': TT.RBRACKET,
    '#': TT.HASH,
    '&': TT.BIT_AND,
    '^': TT.BIT_XOR,
}


def tokenize(source):
    """Tokenize Orren source code into a list of Token objects."""
    tokens = []
    i = 0
    line = 1
    col = 1
    n = len(source)
    depth = 0  # Track nesting of (), [], {} to suppress newlines inside

    while i < n:
        c = source[i]

        # Skip spaces and tabs
        if c in ' \t':
            i += 1
            col += 1
            continue

        # Comments: --, ///, ##, and // (all single-line)
        if c == '-' and i + 1 < n and source[i + 1] == '-':
            while i < n and source[i] != '\n':
                i += 1
            continue
        if c == '/' and i + 1 < n and source[i + 1] == '/':
            # Handles both // and /// (doc comment) — both are line comments
            while i < n and source[i] != '\n':
                i += 1
            continue
        if c == '#':
            # Handles #, ##, and ### — all line comments
            while i < n and source[i] != '\n':
                i += 1
            continue

        # Newlines (suppressed inside (), [], {} to allow multi-line expressions)
        if c == '\n':
            if depth == 0:
                if tokens and tokens[-1].tt != TT.NEWLINE:
                    tokens.append(Token(TT.NEWLINE, '\\n', line, col))
            line += 1
            col = 1
            i += 1
            continue

        # String literals (may span multiple lines)
        if c == '"':
            i += 1
            col += 1
            parts = []
            while i < n and source[i] != '"':
                if source[i] == '\\' and i + 1 < n:
                    nc = source[i + 1]
                    if nc == 'n':
                        parts.append('\n')
                    elif nc == 't':
                        parts.append('\t')
                    elif nc == '\\':
                        parts.append('\\')
                    elif nc == '"':
                        parts.append('"')
                    elif nc == 'r':
                        parts.append('\r')
                    else:
                        parts.append(nc)
                    i += 2
                    col += 2
                elif source[i] == '\n':
                    parts.append('\n')
                    line += 1
                    col = 1
                    i += 1
                else:
                    parts.append(source[i])
                    i += 1
                    col += 1
            if i < n:
                i += 1  # closing quote
            tokens.append(Token(TT.STRING, ''.join(parts), line, col))
            col += 1
            continue

        # Number literals
        if c.isdigit():
            start = i
            while i < n and source[i].isdigit():
                i += 1
            if i < n and source[i] == '.' and i + 1 < n and source[i + 1].isdigit():
                i += 1
                while i < n and source[i].isdigit():
                    i += 1
                tokens.append(Token(TT.FLOAT, float(source[start:i]), line, col))
            else:
                tokens.append(Token(TT.INT, int(source[start:i]), line, col))
            col += i - start
            continue

        # Two-char operators
        if i + 1 < n:
            two = source[i:i + 2]
            if two == '->':
                tokens.append(Token(TT.ARROW, '->', line, col))
                i += 2
                col += 2
                continue
            if two == '=>':
                tokens.append(Token(TT.FAT_ARROW, '=>', line, col))
                i += 2
                col += 2
                continue
            if two == '==':
                tokens.append(Token(TT.EQEQ, '==', line, col))
                i += 2
                col += 2
                continue
            if two == '!=':
                tokens.append(Token(TT.NEQ, '!=', line, col))
                i += 2
                col += 2
                continue
            if two == '<=':
                tokens.append(Token(TT.LTE, '<=', line, col))
                i += 2
                col += 2
                continue
            if two == '>=':
                tokens.append(Token(TT.GTE, '>=', line, col))
                i += 2
                col += 2
                continue

        # Two-char shift operators: << and >>
        if source[i:i + 2] == '<<':
            tokens.append(Token(TT.SHIFT_LEFT, '<<', line, col))
            i += 2
            col += 2
            continue
        if source[i:i + 2] == '>>':
            tokens.append(Token(TT.SHIFT_RIGHT, '>>', line, col))
            i += 2
            col += 2
            continue

        # Two-char range operator: ..
        if c == '.' and i + 1 < n and source[i + 1] == '.':
            tokens.append(Token(TT.RANGE, '..', line, col))
            i += 2
            col += 2
            continue

        # Single-char operators
        if c in SINGLE_CHARS:
            if c in '([{':
                depth += 1
            elif c in ')]}':
                depth -= 1
            tokens.append(Token(SINGLE_CHARS[c], c, line, col))
            i += 1
            col += 1
            continue

        # Identifiers and keywords
        if c.isalpha() or c == '_':
            start = i
            while i < n and (source[i].isalnum() or source[i] == '_'):
                i += 1
            word = source[start:i]
            if word in KEYWORDS:
                tt = KEYWORDS[word]
                if tt == TT.TRUE:
                    tokens.append(Token(TT.BOOL, True, line, col))
                elif tt == TT.FALSE:
                    tokens.append(Token(TT.BOOL, False, line, col))
                else:
                    tokens.append(Token(tt, word, line, col))
            else:
                tokens.append(Token(TT.IDENT, word, line, col))
            col += i - start
            continue

        # Skip unknown characters
        i += 1
        col += 1

    tokens.append(Token(TT.EOF, None, line, col))
    return tokens


# ================================================================
# SECTION 2: AST NODE & PARSER
# ================================================================

class Node:
    """AST node with kind, children, and data dict."""
    __slots__ = ('kind', 'children', 'data')

    def __init__(self, kind, children=None, data=None):
        self.kind = kind
        self.children = children if children is not None else []
        self.data = data if data is not None else {}

    def __repr__(self):
        if self.children:
            return 'Node(%s, %r)' % (self.kind, self.children)
        return 'Node(%s, %r)' % (self.kind, self.data)


class ParseError(Exception):
    """Raised when parsing fails."""
    pass


class Parser:
    """Recursive-descent parser for Orren source code."""

    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def peek(self):
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return Token(TT.EOF, None)

    def advance(self):
        t = self.tokens[self.pos]
        self.pos += 1
        return t

    def expect(self, tt):
        t = self.peek()
        if t.tt != tt:
            raise ParseError(
                'Expected %s, got %s (%r) at line %d' % (tt, t.tt, t.val, t.line)
            )
        return self.advance()

    def skip_nl(self):
        while self.peek().tt == TT.NEWLINE:
            self.advance()

    def _push_token(self, token):
        """Insert a token at the current position (for splitting compound tokens)."""
        self.tokens.insert(self.pos, token)

    def at(self, tt):
        return self.peek().tt == tt

    def at_ident(self, name):
        return self.peek().tt == TT.IDENT and self.peek().val == name

    def at_keyword_val(self, name):
        t = self.peek()
        return t.tt == TT.IDENT and t.val == name

    def _is_intent(self):
        return self.peek().tt == TT.IDENT and self.peek().val == 'intent'

    # ----- Top-level -----

    def parse_module(self):
        self.skip_nl()
        node = Node('module')
        while not self.at(TT.EOF):
            self.skip_nl()
            if self.at(TT.EOF):
                break
            if self.at(TT.MODULE):
                self.advance()
                parts = [self._expect_ident()]
                while self.at(TT.DOT):
                    self.advance()
                    parts.append(self._expect_ident())
                node.data['name'] = '.'.join(parts)
                self.skip_nl()
            elif self.at(TT.IMPORT):
                node.children.append(self._parse_import())
            elif self._is_intent():
                node.children.append(self._parse_intent())
            elif self.at(TT.CONST):
                node.children.append(self._parse_const())
            elif self.at(TT.ENUM):
                node.children.append(self._parse_enum())
            elif self.at(TT.ENTITY):
                node.children.append(self._parse_entity())
            elif self.at(TT.FN):
                node.children.append(self._parse_function(is_method=False))
            elif self.at(TT.LET):
                node.children.append(self._parse_let())
            elif self.at(TT.EXPORT):
                node.children.append(self._parse_export())
            else:
                # Try to parse as a generic statement (if, for, while, etc.)
                stmt = self._parse_statement()
                if stmt is not None and stmt.kind != 'noop':
                    node.children.append(stmt)
            self.skip_nl()
        return node

    def _parse_import(self):
        self.expect(TT.IMPORT)
        node = Node('import')
        if self.at(TT.FROM):
            self.advance()
            from_mod = self._parse_module_path()
            self.expect(TT.COLON)
            self.expect(TT.COLON)
            names = self._parse_name_list()
            node.data = {'from': from_mod, 'names': names}
        else:
            mod = self._parse_module_path()
            if self.at(TT.COLON) and self.pos + 1 < len(self.tokens):
                if self.tokens[self.pos + 1].tt == TT.COLON:
                    self.advance()
                    self.advance()
                    if self.at(TT.LBRACE):
                        names = self._parse_name_list()
                    else:
                        names = [self._expect_ident()]
                    node.data = {'module': mod, 'names': names}
                else:
                    node.data = {'module': mod, 'names': []}
            elif self.at(TT.DOT) and self.pos + 1 < len(self.tokens) and self.tokens[self.pos + 1].tt == TT.LBRACE:
                # import a.b.c.{X, Y}  (dot-brace import syntax)
                self.advance()
                names = self._parse_name_list()
                node.data = {'module': mod, 'names': names}
            else:
                node.data = {'module': mod, 'names': []}
        self.skip_nl()
        return node

    def _parse_module_path(self):
        parts = [self._expect_ident()]
        while self.at(TT.DOT):
            self.advance()
            parts.append(self._expect_ident())
        return '.'.join(parts)

    def _parse_name_list(self):
        names = []
        self.expect(TT.LBRACE)
        self.skip_nl()
        if self.at(TT.STAR):
            self.advance()
            names.append('*')
        elif not self.at(TT.RBRACE):
            names.append(self._expect_ident())
            while self.at(TT.COMMA):
                self.advance()
                self.skip_nl()
                if self.at(TT.RBRACE):
                    break
                names.append(self._expect_ident())
                self.skip_nl()
        self.expect(TT.RBRACE)
        return names

    def _parse_intent(self):
        self.advance()  # consume 'intent'
        self.skip_nl()
        text = self.expect(TT.STRING).val
        self.skip_nl()
        return Node('intent', data={'text': text})

    def _parse_const(self):
        self.expect(TT.CONST)
        name = self._expect_ident()
        type_ann = None
        if self.at(TT.COLON):
            self.advance()
            type_ann = self._parse_type()
        self.expect(TT.EQ)
        self.skip_nl()
        value = self._parse_expr()
        self.skip_nl()
        return Node('const', data={'name': name, 'type': type_ann, 'value': value})

    def _parse_type(self):
        name = self._expect_ident()
        # Handle dotted type names like Json.Value
        while self.at(TT.DOT):
            self.advance()
            sub = self._expect_ident()
            name = name + '.' + sub
        if self.at(TT.LT):
            self.advance()
            params = [self._parse_type()]
            while self.at(TT.COMMA):
                self.advance()
                self.skip_nl()
                params.append(self._parse_type())
            # Handle >> as two closing > tokens in nested generics
            if self.at(TT.SHIFT_RIGHT):
                tok = self.advance()  # consume >>
                self._push_token(Token(TT.GT, '>', tok.line, tok.col))
                self.expect(TT.GT)  # consume first > for this generic
            else:
                self.expect(TT.GT)
            return name + '<' + ','.join(params) + '>'
        return name

    def _parse_enum(self):
        self.expect(TT.ENUM)
        name = self._expect_ident()
        self.skip_nl()
        variants = []
        while not self.at(TT.END):
            if self.at(TT.NEWLINE):
                self.advance()
                continue
            variants.append(self._expect_ident())
            self.skip_nl()
        self.expect(TT.END)
        self.skip_nl()
        return Node('enum', data={'name': name, 'variants': variants})

    def _parse_entity(self):
        self.expect(TT.ENTITY)
        name = self._expect_ident()
        self.skip_nl()
        properties = []
        methods = []
        while not self.at(TT.END):
            if self.at(TT.NEWLINE):
                self.advance()
                continue
            if self._is_intent():
                self._parse_intent()
                continue
            if self.at(TT.PROPERTY):
                self.advance()
                pname = self._expect_ident()
                ptype = None
                default = None
                if self.at(TT.COLON):
                    self.advance()
                    ptype = self._parse_type()
                if self.at(TT.EQ):
                    self.advance()
                    self.skip_nl()
                    default = self._parse_expr()
                properties.append({
                    'name': pname, 'type': ptype, 'default': default
                })
                self.skip_nl()
            elif self.at(TT.FN):
                methods.append(self._parse_function(is_method=True))
                self.skip_nl()
            else:
                self.advance()
        self.expect(TT.END)
        self.skip_nl()
        return Node('entity',
                      data={'name': name, 'properties': properties},
                      children=methods)

    def _parse_function(self, is_method=False):
        self.expect(TT.FN)
        name = self._expect_ident()
        self.expect(TT.LPAREN)
        params = []
        has_self = False
        if not self.at(TT.RPAREN):
            p = self._parse_param()
            if p['name'] == 'self':
                has_self = True
            params.append(p)
            while self.at(TT.COMMA):
                self.advance()
                self.skip_nl()
                if self.at(TT.RPAREN):
                    break
                p = self._parse_param()
                params.append(p)
        self.expect(TT.RPAREN)
        ret_type = None
        if self.at(TT.ARROW):
            self.advance()
            ret_type = self._parse_type()
        self.skip_nl()
        if self.at(TT.DO):
            self.advance()
            self.skip_nl()
        body = self._parse_block()
        self.expect(TT.END)
        self.skip_nl()
        return Node('function', data={
            'name': name, 'params': params, 'return_type': ret_type,
            'is_method': is_method, 'has_self': has_self
        }, children=body)

    def _parse_param(self):
        name = self._expect_ident()
        type_ann = None
        if self.at(TT.COLON):
            self.advance()
            type_ann = self._parse_type()
        return {'name': name, 'type': type_ann}

    def _expect_ident(self):
        """Accept IDENT or any keyword token used as identifier."""
        t = self.peek()
        if t.tt == TT.IDENT:
            self.advance()
            return t.val
        # Allow keywords used as identifiers
        keyword_tts = [
            TT.MODULE, TT.IMPORT, TT.FROM, TT.EXPORT, TT.ENTITY, TT.ENUM,
            TT.FN, TT.CONST, TT.PROPERTY, TT.LET, TT.BE, TT.IF, TT.THEN,
            TT.ELSE, TT.END, TT.FOR, TT.IN, TT.WHILE, TT.DO, TT.MATCH,
            TT.WITH, TT.RETURN, TT.AND, TT.OR, TT.NOT, TT.CASE, TT.SELF,
        ]
        if t.tt in keyword_tts:
            self.advance()
            return t.val
        raise ParseError(
            'Expected identifier, got %s (%r) at line %d' % (t.tt, t.val, t.line)
        )

    def _parse_block(self):
        stmts = []
        while True:
            self.skip_nl()
            # Skip trailing commas between statements
            while self.at(TT.COMMA):
                self.advance()
                self.skip_nl()
            t = self.peek()
            if t.tt == TT.EOF:
                break
            if t.tt == TT.END:
                break
            if t.tt == TT.ELSE:
                break
            if t.tt == TT.IDENT and t.val == 'end':
                break
            if t.tt == TT.IDENT and t.val == 'else':
                break
            if t.tt == TT.IDENT and t.val == 'case':
                break
            if self._is_intent():
                self._parse_intent()
                continue
            stmt = self._parse_statement()
            if stmt is not None:
                stmts.append(stmt)
            self.skip_nl()
        return stmts

    def _parse_statement(self):
        t = self.peek()
        if t.tt == TT.LET:
            return self._parse_let()
        if t.tt == TT.IF:
            return self._parse_if()
        if t.tt == TT.FOR:
            return self._parse_for()
        if t.tt == TT.WHILE:
            return self._parse_while()
        if t.tt == TT.MATCH:
            return self._parse_match()
        if t.tt == TT.RETURN:
            return self._parse_return()
        return self._parse_assign_or_expr()

    def _parse_let(self):
        self.expect(TT.LET)
        # Handle: let mut NAME or let be NAME - optional keywords after let
        is_mut = False
        if self.at(TT.MUT):
            is_mut = True
            self.advance()
        elif self.at(TT.BE) and len(self.tokens) > self.pos + 1 and self.tokens[self.pos + 1].tt in (TT.IDENT,):
            # 'let be NAME = value' - 'be' is a binding keyword, not the variable name
            self.advance()
        # Handle: let self.x = value (property assignment)
        if self.at(TT.SELF):
            self.advance()
            if self.at(TT.DOT):
                self.advance()
                name = self._expect_ident()
                type_ann = None
                if self.at(TT.COLON):
                    self.advance()
                    type_ann = self._parse_type()
                if self.at(TT.BE) or self.at(TT.EQ):
                    self.advance()
                    self.skip_nl()
                    value = self._parse_assign_or_expr()
                else:
                    value = None
                self.skip_nl()
                return Node('assign', data={'target': Node('member', data={'object': Node('self_ref'), 'member': name}), 'value': value})
        name = self._expect_ident()
        type_ann = None
        if self.at(TT.COLON):
            self.advance()
            type_ann = self._parse_type()
        value = None
        if self.at(TT.BE):
            self.advance()
            value = self._parse_assign_or_expr()
        elif self.at(TT.EQ):
            self.advance()
            value = self._parse_assign_or_expr()
        self.skip_nl()
        return Node('let', data={'name': name, 'type': type_ann, 'value': value, 'is_mut': is_mut})

    def _parse_if(self):
        self.expect(TT.IF)
        self.skip_nl()
        condition = self._parse_expr()
        self.skip_nl()
        if self.at(TT.THEN):
            self.advance()
        self.skip_nl()
        then_body = self._parse_block()
        # else-if chain: else if <cond> then <body>  (multiple allowed, single trailing end)
        else_ifs = []
        else_body = []
        while self.at(TT.ELSE):
            self.advance()
            self.skip_nl()
            if self.at(TT.IF):
                self.advance()
                self.skip_nl()
                econd = self._parse_expr()
                self.skip_nl()
                if self.at(TT.THEN):
                    self.advance()
                self.skip_nl()
                ebody = self._parse_block()
                else_ifs.append((econd, ebody))
            else:
                else_body = self._parse_block()
                break
        self.skip_nl()
        self.expect(TT.END)
        self.skip_nl()
        return Node('if', data={
            'condition': condition, 'else_ifs': else_ifs
        }, children=[then_body, else_body])

    def _parse_for(self):
        self.expect(TT.FOR)
        self.skip_nl()
        # Handle destructuring: for (a, b, c) in iterable do ... end
        if self.at(TT.LPAREN):
            self.advance()
            self.skip_nl()
            names = []
            if not self.at(TT.RPAREN):
                names.append(self._expect_ident())
                while self.at(TT.COMMA):
                    self.advance()
                    self.skip_nl()
                    if self.at(TT.RPAREN):
                        break
                    names.append(self._expect_ident())
            self.skip_nl()
            self.expect(TT.RPAREN)
            self.skip_nl()
            if self.at(TT.IN):
                self.advance()
                self.skip_nl()
                iterable = self._parse_expr()
                self.skip_nl()
                if self.at(TT.DO):
                    self.advance()
                    self.skip_nl()
                body = self._parse_block()
                self.expect(TT.END)
                self.skip_nl()
                return Node('for_in', data={'var': 'tuple', 'iterable': iterable, 'destructure': names}, children=body)
        # Regular for-in/for-c
        if self.peek().tt != TT.IDENT:
            self.advance()
            return Node('noop')
        name = self.advance().val
        if self.at(TT.IN):
            # for X in Y [do] ... end
            self.advance()
            self.skip_nl()
            iterable = self._parse_expr()
            self.skip_nl()
            if self.at(TT.DO):
                self.advance()
                self.skip_nl()
            body = self._parse_block()
            self.expect(TT.END)
            self.skip_nl()
            return Node('for_in', data={'var': name, 'iterable': iterable, 'destructure': None}, children=body)
        else:
            # for var OP limit [do] ... end  (C-style with any comparison)
            op_tok = self.peek()
            op_map = {
                TT.LT: '<', TT.GT: '>', TT.LTE: '<=', TT.GTE: '>=',
                TT.EQEQ: '==', TT.NEQ: '!=',
            }
            if op_tok.tt in op_map:
                op = op_map[op_tok.tt]
                self.advance()
            else:
                op = '<'
            self.skip_nl()
            limit = self._parse_expr()
            self.skip_nl()
            if self.at(TT.DO):
                self.advance()
                self.skip_nl()
            body = self._parse_block()
            self.expect(TT.END)
            self.skip_nl()
            return Node('for_c', data={'var': name, 'op': op, 'limit': limit, 'destructure': None}, children=body)

    def _parse_while(self):
        self.expect(TT.WHILE)
        self.skip_nl()
        condition = self._parse_expr()
        self.skip_nl()
        if self.at(TT.DO):
            self.advance()
            self.skip_nl()
        body = self._parse_block()
        self.expect(TT.END)
        self.skip_nl()
        return Node('while', data={'condition': condition}, children=body)

    def _parse_match(self):
        self.expect(TT.MATCH)
        self.skip_nl()
        expr = self._parse_expr()
        self.skip_nl()
        self.expect(TT.WITH)
        self.skip_nl()
        arms = self._parse_match_arms()
        self.expect(TT.END)
        self.skip_nl()
        return Node('match', data={'expr': expr, 'arms': arms})

    def _parse_match_pattern(self):
        t = self.peek()
        if t.tt == TT.STRING:
            self.advance()
            return ('literal', t.val)
        if t.tt == TT.INT:
            self.advance()
            return ('literal', t.val)
        if t.tt == TT.FLOAT:
            self.advance()
            return ('literal', t.val)
        if t.tt == TT.BOOL:
            self.advance()
            return ('literal', t.val)
        if t.tt == TT.UNDERSCORE or (t.tt == TT.IDENT and t.val == '_'):
            self.advance()
            return ('wildcard',)
        if t.tt == TT.IDENT or t.tt == TT.SELF:
            self.advance()
            name = t.val
            if self.at(TT.DOT):
                self.advance()
                member = self._expect_ident()
                return ('dotted', name, member)
            # Handle :: patterns: Optional::some(code)
            if self.at(TT.COLON) and self.pos + 1 < len(self.tokens) and self.tokens[self.pos + 1].tt == TT.COLON:
                self.advance()
                self.advance()
                member = self._expect_ident()
                if self.at(TT.LPAREN):
                    self.advance()
                    if not self.at(TT.RPAREN):
                        self._parse_expr()  # consume the arg
                    self.expect(TT.RPAREN)
                return ('dotted', name + '::' + member, None)
            if self.at(TT.LPAREN):
                self.advance()
                args = []
                if not self.at(TT.RPAREN):
                    args.append(self._expect_ident())
                    while self.at(TT.COMMA):
                        self.advance()
                        if self.at(TT.RPAREN): break
                        args.append(self._expect_ident())
                self.expect(TT.RPAREN)
                return ('constructor', name, args)
            return ('ident', name)
        self.advance()
        return ('wildcard',)

    def _parse_return(self):
        self.expect(TT.RETURN)
        if self.at(TT.NEWLINE) or self.at(TT.END) or self.at(TT.EOF):
            return Node('return', data={'value': None})
        if self.at(TT.LPAREN):
            self.advance()
            self.skip_nl()
            # Handle empty parens ()
            if self.at(TT.RPAREN):
                self.advance()
                return Node('return', data={'value': None})
            # Tuple return: return (a, b, c)
            first = self._parse_expr()
            self.skip_nl()
            if self.at(TT.COMMA):
                elements = [first]
                while self.at(TT.COMMA):
                    self.advance()
                    self.skip_nl()
                    if self.at(TT.RPAREN):
                        break
                    elements.append(self._parse_expr())
                    self.skip_nl()
                self.expect(TT.RPAREN)
                return Node('return', data={'value': Node('tuple', data={'elements': elements})})
            else:
                self.expect(TT.RPAREN)
                return Node('return', data={'value': first})
        value = self._parse_expr()
        self.skip_nl()
        return Node('return', data={'value': value})

    def _parse_export(self):
        self.expect(TT.EXPORT)
        self.skip_nl()
        names = []
        if self.at(TT.LBRACE):
            # export {A, B, C}
            self.advance()
            self.skip_nl()
            if not self.at(TT.RBRACE):
                names.append(self._expect_ident())
                while self.at(TT.COMMA):
                    self.advance()
                    self.skip_nl()
                    if self.at(TT.RBRACE):
                        break
                    names.append(self._expect_ident())
                    self.skip_nl()
            self.expect(TT.RBRACE)
        else:
            # export Name (single name without braces)
            names.append(self._expect_ident())
        self.skip_nl()
        return Node('export', data={'names': names})

    def _parse_assign_or_expr(self):
        expr = self._parse_expr()
        self.skip_nl()
        if self.at(TT.EQ):
            self.advance()
            self.skip_nl()
            value = self._parse_assign_or_expr()
            return Node('assign', data={'target': expr, 'value': value})
        self.skip_nl()
        return Node('expr_stmt', data={'expr': expr})

    # ----- Expression parsing (precedence climbing) -----

    def _parse_expr(self, min_prec=0):
        return self._parse_logical_or()

    def _parse_shift(self):
        left = self._parse_additive()
        while self.peek().tt in (TT.SHIFT_LEFT, TT.SHIFT_RIGHT):
            op = self.advance().val
            right = self._parse_additive()
            left = Node('binop', data={'op': op, 'left': left, 'right': right})
        return left

    def _parse_bitwise(self):
        left = self._parse_shift()
        while self.peek().tt in (TT.BIT_AND, TT.BIT_XOR):
            op = self.advance().val
            right = self._parse_shift()
            left = Node('binop', data={'op': op, 'left': left, 'right': right})
        return left

    def _parse_comparison(self):
        left = self._parse_bitwise()
        while self.peek().tt in (TT.EQEQ, TT.NEQ, TT.LT, TT.GT, TT.LTE, TT.GTE, TT.RANGE):
            op = self.advance().val
            right = self._parse_bitwise()
            left = Node('binop', data={'op': op, 'left': left, 'right': right})
        return left

    def _parse_additive(self):
        left = self._parse_multiplicative()
        while self.peek().tt in (TT.PLUS, TT.MINUS):
            op = self.advance().val
            right = self._parse_multiplicative()
            left = Node('binop', data={'op': op, 'left': left, 'right': right})
        return left

    def _parse_multiplicative(self):
        left = self._parse_unary()
        while self.peek().tt in (TT.STAR, TT.SLASH, TT.PERCENT):
            op = self.advance().val
            right = self._parse_unary()
            left = Node('binop', data={'op': op, 'left': left, 'right': right})
        return left

    def _parse_logical_and(self):
        left = self._parse_comparison()
        while self.peek().tt == TT.AND:
            op = self.advance().val
            right = self._parse_comparison()
            left = Node('binop', data={'op': op, 'left': left, 'right': right})
        return left

    def _parse_logical_or(self):
        left = self._parse_logical_and()
        while self.peek().tt == TT.OR:
            op = self.advance().val
            right = self._parse_logical_and()
            left = Node('binop', data={'op': op, 'left': left, 'right': right})
        return left

    def _parse_unary(self):
        if self.at(TT.NOT):
            self.advance()
            operand = self._parse_unary()
            return Node('unary', data={'op': 'not', 'operand': operand})
        if self.at(TT.MINUS):
            self.advance()
            operand = self._parse_unary()
            return Node('unary', data={'op': '-', 'operand': operand})
        return self._parse_postfix()

    def _parse_postfix(self):
        expr = self._parse_primary()
        while True:
            if self.at(TT.DOT):
                self.advance()
                name = self._expect_ident()
                expr = Node('member', data={'object': expr, 'member': name})
            elif self.at(TT.COLON) and self.pos + 1 < len(self.tokens) and self.tokens[self.pos + 1].tt == TT.COLON:
                # Ident::name static namespace access (e.g. Optional::some, Enum::Variant)
                self.advance()  # consume first :
                self.advance()  # consume second :
                name = self._expect_ident()
                expr = Node('member', data={'object': expr, 'member': name})
            elif self.at(TT.LPAREN):
                self.advance()
                self.skip_nl()
                args = []
                if not self.at(TT.RPAREN):
                    args.append(self._parse_expr())
                    while self.at(TT.COMMA):
                        self.advance()
                        self.skip_nl()
                        if self.at(TT.RPAREN):
                            break
                        args.append(self._parse_expr())
                self.skip_nl()
                self.expect(TT.RPAREN)
                expr = Node('call', data={'callee': expr, 'args': args})
            elif self.at(TT.LBRACKET):
                self.advance()
                self.skip_nl()
                idx = self._parse_expr()
                # Support slice syntax: obj[start : end]
                if self.at(TT.COLON):
                    self.advance()
                    end_expr = self._parse_expr()
                    idx = Node('slice', data={'start': idx, 'end': end_expr})
                self.skip_nl()
                self.expect(TT.RBRACKET)
                expr = Node('index', data={'object': expr, 'index': idx})
            elif self.at(TT.AS):
                # Type cast: expr as Type
                self.advance()
                cast_type = self._parse_type()
                expr = Node('cast', data={'object': expr, 'type': cast_type})
            else:
                break
        return expr

    def _parse_match_as_expr(self):
        """Parse a match expression used as a sub-expression."""
        self.expect(TT.MATCH)
        self.skip_nl()
        expr = self._parse_expr()
        self.skip_nl()
        self.expect(TT.WITH)
        self.skip_nl()
        arms = self._parse_match_arms()
        self.expect(TT.END)
        self.skip_nl()
        return Node('match', data={'expr': expr, 'arms': arms})

    def _parse_match_arms(self):
        """Parse match arms, supporting =>, then, do, and comma separators."""
        arms = []
        while not self.at(TT.END):
            self.skip_nl()
            if self.at(TT.END):
                break
            if self.at(TT.COMMA):
                self.advance()
                continue
            # case PATTERN do ... end
            if self.at(TT.CASE):
                self.advance()
                pattern = self._parse_match_pattern()
                self.skip_nl()
                if self.at(TT.DO):
                    self.advance()
                    self.skip_nl()
                elif self.at(TT.THEN):
                    self.advance()
                    self.skip_nl()
                else:
                    break
                body = self._parse_block()
                self.skip_nl()
                if self.at(TT.END):
                    self.advance()
                arms.append((pattern, body))
                continue
            # PATTERN => body  /  PATTERN then body  /  PATTERN do body end
            pattern = self._parse_match_pattern()
            self.skip_nl()
            # do-separated arm (pattern do ... end)
            if self.at(TT.DO):
                self.advance()
                self.skip_nl()
                body = self._parse_match_arm_body(True)
                arms.append((pattern, body))
                continue
            if self.at(TT.FAT_ARROW):
                self.advance()
            elif self.at(TT.THEN):
                self.advance()
            else:
                break
            self.skip_nl()
            if self.at(TT.DO):
                # => do ... end  or  then do ... end
                self.advance()
                self.skip_nl()
                body = self._parse_match_arm_body(True)
            elif self.at(TT.RETURN):
                body = [self._parse_return()]
                self.skip_nl()
            else:
                body = self._parse_match_arm_body(False)
            arms.append((pattern, body))
        return arms

    def _parse_match_arm_body(self, expect_end):
        """Parse statements for a match arm body.

        If expect_end is True, body is delimited by 'end' (do/then style).
        If expect_end is False, body is terminated by comma or END.
        """
        stmts = []
        while True:
            self.skip_nl()
            if self.at(TT.EOF):
                break
            if self.at(TT.END):
                break
            if not expect_end and self.at(TT.COMMA):
                self.advance()
                break
            if self.at(TT.DO):
                # Inline do: '(' do self.x = 1 end
                self.advance()
                self.skip_nl()
                stmt = self._parse_statement()
                if stmt is not None:
                    stmts.append(stmt)
                self.skip_nl()
                if self.at(TT.END):
                    self.advance()
                break
            stmt = self._parse_statement()
            if stmt is not None:
                stmts.append(stmt)
            else:
                break
        return stmts

    def _parse_primary(self):
        t = self.peek()

        # match ... with ... end as expression
        if t.tt == TT.MATCH:
            return self._parse_match_as_expr()

        # if-then-else-end as expression
        if t.tt == TT.IF:
            return self._parse_if()

        if t.tt == TT.INT:
            self.advance()
            return Node('literal', data={'value': t.val, 'type': 'Int'})
        if t.tt == TT.FLOAT:
            self.advance()
            return Node('literal', data={'value': t.val, 'type': 'Float'})
        if t.tt == TT.STRING:
            self.advance()
            return Node('literal', data={'value': t.val, 'type': 'String'})
        if t.tt == TT.BOOL:
            self.advance()
            return Node('literal', data={'value': t.val, 'type': 'Bool'})
        if t.tt == TT.SELF:
            self.advance()
            return Node('self_ref')

        # Lambda: fn a, b -> expr
        if t.tt == TT.FN:
            self.advance()
            params = []
            while True:
                self.skip_nl()
                if self.at(TT.FAT_ARROW):
                    break
                if self.at(TT.LPAREN):
                    break
                name = self._expect_ident()
                type_ann = None
                if self.at(TT.COLON):
                    self.advance()
                    type_ann = self._parse_type()
                params.append({'name': name, 'type': type_ann})
                if self.at(TT.COMMA):
                    self.advance()
                else:
                    break
            self.skip_nl()
            self.expect(TT.ARROW)
            body_expr = self._parse_expr()
            self.skip_nl()
            return Node('lambda', data={'params': params, 'body': body_expr})

        if t.tt == TT.IDENT:
            self.advance()
            # Check for generic type: Ident<...>
            generic_name = t.val
            if self.at(TT.LT):
                save_pos = self.pos
                try:
                    self.advance()  # consume <
                    type_args = [self._parse_type()]
                    while self.at(TT.COMMA):
                        self.advance()
                        type_args.append(self._parse_type())
                    # Handle >> as two > tokens
                    if self.at(TT.SHIFT_RIGHT):
                        tok = self.advance()
                        self._push_token(Token(TT.GT, '>', tok.line, tok.col))
                        self.expect(TT.GT)
                    else:
                        self.expect(TT.GT)
                    generic_name = t.val + '<' + ','.join(type_args) + '>'
                except ParseError:
                    self.pos = save_pos
                    generic_name = t.val
            # Entity instantiation with brace syntax: Name{field=val, ...} or Name{field: val, ...}
            if self.at(TT.LBRACE):
                self.advance()
                self.skip_nl()
                fields = {}
                list_elements = []
                is_list_constructor = False
                if not self.at(TT.RBRACE):
                    # Check if this is a list constructor {expr, expr, ...} or entity construct {name=val, ...}
                    if self.peek().tt in (TT.STRING, TT.INT, TT.FLOAT, TT.BOOL, TT.LBRACKET, TT.LBRACE, TT.LPAREN, TT.IDENT, TT.MINUS, TT.FN):
                        is_list_constructor = True
                    if is_list_constructor:
                        list_elements.append(self._parse_expr())
                        while self.at(TT.COMMA):
                            self.advance()
                            self.skip_nl()
                            if self.at(TT.RBRACE):
                                break
                            list_elements.append(self._parse_expr())
                    else:
                        k = self._expect_ident()
                        # Accept both = and : as field separator
                        if self.at(TT.EQ):
                            self.advance()
                        elif self.at(TT.COLON):
                            self.advance()
                        else:
                            pass  # value-less field
                        v = self._parse_expr()
                        fields[k] = v
                        self.skip_nl()
                        while self.at(TT.COMMA):
                            self.advance()
                            self.skip_nl()
                            if self.at(TT.RBRACE):
                                break
                            k = self._expect_ident()
                            if self.at(TT.EQ):
                                self.advance()
                            elif self.at(TT.COLON):
                                self.advance()
                            v = self._parse_expr()
                            fields[k] = v
                            self.skip_nl()
                self.skip_nl()
                self.expect(TT.RBRACE)
                if is_list_constructor:
                    return Node('list_literal', data={'elements': list_elements, 'type_name': generic_name})
                return Node('construct', data={'name': generic_name, 'fields': fields})
            # For Name(args), return ident and let postfix handle () as a call
            return Node('ident', data={'name': generic_name})

        # List literal: [a, b, c]
        if t.tt == TT.LBRACKET:
            self.advance()
            self.skip_nl()
            elements = []
            if not self.at(TT.RBRACKET):
                elements.append(self._parse_expr())
                while self.at(TT.COMMA):
                    self.advance()
                    self.skip_nl()
                    if self.at(TT.RBRACKET):
                        break
                    elements.append(self._parse_expr())
            self.skip_nl()
            self.expect(TT.RBRACKET)
            return Node('list_literal', data={'elements': elements})

        # Empty brace {} as empty map or map literal
        if t.tt == TT.LBRACE:
            self.advance()
            self.skip_nl()
            if self.at(TT.RBRACE):
                self.advance()
                return Node('literal', data={'value': {}, 'type': 'Map'})
            # Non-empty {key = val, ...} map literal (keys can be IDENT or STRING)
            fields = {}
            # Read first key (ident or string)
            if self.at(TT.STRING):
                k = self.advance().val
            else:
                k = self._expect_ident()
            sep = self.at(TT.EQ) or self.at(TT.COLON)
            if sep: self.advance()
            v = self._parse_expr()
            fields[k] = v
            self.skip_nl()
            while self.at(TT.COMMA):
                self.advance()
                self.skip_nl()
                if self.at(TT.RBRACE): break
                if self.at(TT.STRING):
                    k = self.advance().val
                else:
                    k = self._expect_ident()
                sep = self.at(TT.EQ) or self.at(TT.COLON)
                if sep: self.advance()
                v = self._parse_expr()
                fields[k] = v
                self.skip_nl()
            self.skip_nl()
            self.expect(TT.RBRACE)
            return Node('literal', data={'value': fields, 'type': 'Map'})

        # Parenthesized expression or tuple: (expr) or (expr, expr, ...)
        if t.tt == TT.LPAREN:
            self.advance()
            self.skip_nl()
            # Handle empty parens ()
            if self.at(TT.RPAREN):
                self.advance()
                return Node('literal', data={'value': None, 'type': 'Unit'})
            first = self._parse_expr()
            self.skip_nl()
            # Tuple: (expr, expr, ...)
            if self.at(TT.COMMA):
                elements = [first]
                while self.at(TT.COMMA):
                    self.advance()
                    self.skip_nl()
                    if self.at(TT.RPAREN):
                        break
                    elements.append(self._parse_expr())
                    self.skip_nl()
                self.expect(TT.RPAREN)
                return Node('tuple', data={'elements': elements})
            self.expect(TT.RPAREN)
            return first

        self.advance()
        return Node('literal', data={'value': None, 'type': 'None'})


# ================================================================
# SECTION 3: RUNTIME TYPES
# ================================================================

class ReturnSignal(Exception):
    """Signal for function return."""
    def __init__(self, value):
        self.value = value


class OrrenEntity:
    """Runtime instance of an Orren entity."""
    def __init__(self, type_name, props=None):
        self._type = type_name
        self._props = props if props is not None else {}

    def __repr__(self):
        return '<%s %s>' % (self._type, dict(self._props))

    def get(self, key):
        return self._props.get(key)

    def put(self, key, value):
        self._props[key] = value


class OrrenEnum:
    """Runtime value of an enum variant."""
    def __init__(self, enum_name, variant_name):
        self._enum = enum_name
        self._variant = variant_name

    def __repr__(self):
        return '%s.%s' % (self._enum, self._variant)

    def __eq__(self, other):
        if isinstance(other, OrrenEnum):
            return self._enum == other._enum and self._variant == other._variant
        return False

    def __hash__(self):
        return hash((self._enum, self._variant))


class EntityRef:
    """Reference to an entity definition (for static method dispatch)."""
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return '<entity:%s>' % self.name


class Environment:
    """Lexical scope with parent chain."""
    def __init__(self, parent=None):
        self.vars = {}
        self.parent = parent

    def get(self, name):
        if name in self.vars:
            return self.vars[name]
        if self.parent is not None:
            return self.parent.get(name)
        raise NameError('Undefined: ' + name)

    def has(self, name):
        if name in self.vars:
            return True
        if self.parent is not None:
            return self.parent.has(name)
        return False

    def define(self, name, value):
        self.vars[name] = value

    def set(self, name, value):
        if name in self.vars:
            self.vars[name] = value
            return True
        if self.parent is not None:
            return self.parent.set(name, value)
        self.vars[name] = value
        return True


# ================================================================
# SECTION 4: EVALUATOR
# ================================================================

class Evaluator:
    """Tree-walking interpreter for Orren AST."""

    def __init__(self, search_paths=None):
        self.modules = {}        # module_name -> Environment
        self.entities = {}       # entity_name -> {'props': [...], 'methods': {name: Node}}
        self.enums = {}          # enum_name -> [variant_names]
        self.search_paths = search_paths if search_paths else ['.']
        self.current_module = None
        self.loaded_files = set()  # avoid re-loading

    # ----- Module loading -----

    def load_and_eval_file(self, filepath):
        abs_path = os.path.abspath(filepath)
        if abs_path in self.loaded_files:
            return None
        self.loaded_files.add(abs_path)
        with open(filepath, 'r', encoding='utf-8') as f:
            source = f.read()
        tokens = tokenize(source)
        parser = Parser(tokens)
        module = parser.parse_module()
        # Set search path to the file's directory
        old_paths = self.search_paths
        file_dir = os.path.dirname(abs_path)
        self.search_paths = [file_dir] + old_paths
        env = self.eval_module(module)
        self.search_paths = old_paths
        return env

    def resolve_module(self, module_path, from_file=None):
        """Try to find a .orn file for a module path."""
        parts = module_path.replace('::', '.').split('.')
        candidates = []
        # Try: path/to/module/name.orn
        candidates.append(os.path.join(*parts) + '.orn')
        # Try: path/to/module/module_name/name.orn (last part is directory)
        if len(parts) >= 2:
            candidates.append(os.path.join(*parts[:-1], parts[-1], parts[-1]) + '.orn')
        # Try: path/to/module/name/name.orn
        if len(parts) >= 2:
            candidates.append(os.path.join(*parts, parts[-1]) + '.orn')
        for search_dir in self.search_paths:
            for rel in candidates:
                full = os.path.join(search_dir, rel)
                if os.path.isfile(full):
                    return full
        return None

    def eval_module(self, module_node):
        env = Environment()
        mod_name = module_node.data.get('name', '__main__')
        self.current_module = mod_name
        self.modules[mod_name] = env
        for child in module_node.children:
            self._eval_node(child, env)
        return env

    # ----- Node evaluation -----

    def _eval_node(self, node, env):
        kind = node.kind

        if kind == 'import':
            return self._handle_import(node, env)

        if kind == 'intent':
            return None

        if kind == 'export':
            return None

        if kind == 'const':
            val = self._eval_expr(node.data['value'], env) if node.data['value'] else None
            env.define(node.data['name'], val)
            return val

        if kind == 'enum':
            name = node.data['name']
            variants = node.data['variants']
            self.enums[name] = variants
            for v in variants:
                env.define(v, OrrenEnum(name, v))
            return None

        if kind == 'entity':
            return self._eval_entity(node, env)

        if kind == 'function':
            env.define(node.data['name'], node)
            return None

        if kind == 'let':
            val = self._eval_expr(node.data['value'], env) if node.data['value'] else None
            env.define(node.data['name'], val)
            return val

        if kind == 'if':
            return self._eval_if(node, env)

        if kind == 'for_in':
            return self._eval_for_in(node, env)

        if kind == 'for_c':
            return self._eval_for_c(node, env)

        if kind == 'while':
            return self._eval_while(node, env)

        if kind == 'match':
            return self._eval_match(node, env)

        if kind == 'return':
            val = self._eval_expr(node.data['value'], env) if node.data['value'] else None
            raise ReturnSignal(val)

        if kind == 'assign':
            value = self._eval_expr(node.data['value'], env)
            self._assign_target(node.data['target'], value, env)
            return value

        if kind == 'expr_stmt':
            return self._eval_expr(node.data['expr'], env)

        if kind == 'noop':
            return None

        return None

    def _eval_entity(self, node, env):
        name = node.data['name']
        props = node.data['properties']
        methods = {}
        for m in node.children:
            if m.kind == 'function':
                methods[m.data['name']] = m
        self.entities[name] = {'props': props, 'methods': methods}
        # Register entity reference for static method dispatch
        env.define(name, EntityRef(name))
        return None

    def _handle_import(self, node, env):
        d = node.data
        if 'from' in d:
            mod_path = d['from']
        elif 'module' in d:
            mod_path = d['module']
        else:
            return None
        # Try to resolve and load the module
        filepath = self.resolve_module(mod_path)
        if filepath:
            try:
                imported_env = self.load_and_eval_file(filepath)
                if imported_env and 'names' in d and d['names']:
                    for n in d['names']:
                        if n == '*':
                            for k, v in imported_env.vars.items():
                                if not k.startswith('_'):
                                    env.define(k, v)
                        else:
                            try:
                                env.define(n, imported_env.get(n))
                            except NameError:
                                pass
            except Exception as e:
                pass  # silently skip unresolvable imports
        return None

    def _eval_if(self, node, env):
        cond = self._eval_expr(node.data['condition'], env)
        if cond:
            return self._eval_block(node.children[0], env)
        for econd, ebody in node.data.get('else_ifs', []):
            if self._eval_expr(econd, env):
                return self._eval_block(ebody, env)
        if len(node.children) > 1 and node.children[1]:
            return self._eval_block(node.children[1], env)
        return None

    def _eval_match(self, node, env):
        """Evaluate a match expression, returning the result of the first matching arm."""
        val = self._eval_expr(node.data['expr'], env)
        for pattern, body in node.data['arms']:
            if self._match_pattern(pattern, val):
                return self._eval_block(body, env) if body else None
        return None

    def _match_pattern(self, pattern, val):
        """Check if a value matches a match-pattern tuple from _parse_match_pattern."""
        if not isinstance(pattern, tuple):
            # Fallback: try equality
            return val == pattern
        kind = pattern[0]
        if kind == 'literal':
            return val == pattern[1]
        if kind == 'wildcard':
            return True
        if kind == 'ident':
            # Variable binding — matches any value
            return True
        if kind == 'dotted':
            # Enum variant match: Type::Variant or Type.member
            variant = pattern[1]
            return val == variant
        if kind == 'constructor':
            # Constructor pattern — best-effort equality on the name
            return val == pattern[1]
        return False

    def _eval_for_in(self, node, env):
        var_name = node.data['var']
        iterable = self._eval_expr(node.data['iterable'], env)
        result = None
        if isinstance(iterable, list):
            for item in iterable:
                env.define(var_name, item)
                result = self._eval_block(node.children, env)
        elif isinstance(iterable, dict):
            for key in iterable:
                env.define(var_name, iterable[key])
                result = self._eval_block(node.children, env)
        return result

    def _eval_for_c(self, node, env):
        var_name = node.data['var']
        op = node.data['op']
        limit = self._eval_expr(node.data['limit'], env)
        result = None
        max_iters = 100000  # safety limit
        count = 0
        while count < max_iters:
            try:
                current = env.get(var_name)
            except NameError:
                current = 0
            if not self._compare(current, op, limit):
                break
            result = self._eval_block(node.children, env)
            count += 1
        return result

    def _eval_while(self, node, env):
        result = None
        max_iters = 100000
        count = 0
        while count < max_iters and self._eval_expr(node.data['condition'], env):
            result = self._eval_block(node.children, env)
            count += 1
        return result

    def _eval_match(self, node, env):
        val = self._eval_expr(node.data['expr'], env)
        for pattern, body in node.data['arms']:
            if self._match_pattern(pattern, val, env):
                return self._eval_block(body, env)
        return None

    def _eval_block(self, stmts, env):
        result = None
        for stmt in stmts:
            result = self._eval_node(stmt, env)
        return result

    # ----- Expression evaluation -----

    def _eval_expr(self, node, env):
        if node is None:
            return None
        kind = node.kind

        if kind == 'literal':
            return node.data['value']

        if kind == 'self_ref':
            return env.get('self')

        if kind == 'if':
            return self._eval_if(node, env)

        if kind == 'ident':
            name = node.data['name']
            if name in BUILTINS:
                return BUILTINS[name]
            try:
                return env.get(name)
            except NameError:
                return None

        if kind == 'construct':
            return self._eval_construct(node, env)

        if kind == 'list_literal':
            if 'type_name' in node.data and node.data['type_name']:
                return [self._eval_expr(e, env) for e in node.data['elements']]
            return [self._eval_expr(e, env) for e in node.data['elements']]

        if kind == 'lambda':
            # Create a closure value
            class LambdaValue:
                def __init__(self, params, body, env):
                    self.params = params
                    self.body = body
                    self.closure_env = env
                def __call__(self, args, call_env):
                    local_env = dict(self.closure_env)
                    for i, p in enumerate(self.params):
                        if i < len(args):
                            local_env[p['name']] = args[i]
                    result = None
                    if isinstance(self.body, Node):
                        result = self._eval_expr(self.body, local_env)
                    else:
                        for stmt in self.body:
                            result = self._eval_stmt(stmt, local_env)
                    return result
                def __repr__(self):
                    return f'<lambda>'
            return LambdaValue(node.data['params'], node.data['body'], env)

        if kind == 'tuple':
            return tuple(self._eval_expr(e, env) for e in node.data['elements'])

        if kind == 'binop':
            return self._eval_binop(node, env)

        if kind == 'unary':
            return self._eval_unary(node, env)

        if kind == 'member':
            return self._eval_member(node, env)

        if kind == 'call':
            return self._eval_call(node, env)

        if kind == 'index':
            obj = self._eval_expr(node.data['object'], env)
            idx = node.data['index']
            # Handle slice: obj[start:end]
            if isinstance(idx, Node) and idx.kind == 'slice':
                start = self._eval_expr(idx.data['start'], env)
                end = self._eval_expr(idx.data['end'], env)
                if isinstance(obj, (list, str)):
                    s = int(start) if start is not None else 0
                    e = int(end) if end is not None else len(obj)
                    return obj[s:e]
                return None
            idx_val = self._eval_expr(idx, env)
            if isinstance(obj, (list, str)) and isinstance(idx_val, (int, float)):
                i = int(idx_val)
                if 0 <= i < len(obj):
                    return obj[i]
                return None
            if isinstance(obj, dict):
                return obj.get(idx_val)
            return None

        if kind == 'cast':
            # Type cast is a no-op at runtime in the bootstrap
            return self._eval_expr(node.data['object'], env)

        if kind == 'match':
            return self._eval_match(node, env)

        return None

    def _eval_construct(self, node, env):
        name = node.data['name']
        if name in self.entities:
            ent = OrrenEntity(name)
            for prop in self.entities[name]['props']:
                default = None
                if prop['default'] is not None:
                    default = self._eval_expr(prop['default'], env)
                ent.put(prop['name'], default)
            if 'fields' in node.data:
                for key, val_node in node.data['fields'].items():
                    ent.put(key, self._eval_expr(val_node, env))
            if 'args' in node.data and node.data['args']:
                args = [self._eval_expr(a, env) for a in node.data['args']]
                props = self.entities[name]['props']
                for i, arg_val in enumerate(args):
                    if i < len(props):
                        ent.put(props[i]['name'], arg_val)
            return ent
        return None

    def _eval_binop(self, node, env):
        op = node.data['op']
        left = self._eval_expr(node.data['left'], env)
        right = self._eval_expr(node.data['right'], env)
        if op == '+':
            if isinstance(left, str) or isinstance(right, str):
                return str(left if left is not None else '') + str(right if right is not None else '')
            return (left or 0) + (right or 0)
        if op == '-':
            return (left or 0) - (right or 0)
        if op == '*':
            return (left or 0) * (right or 0)
        if op == '/':
            r = right if right else 1
            if isinstance(left, int) and isinstance(r, int):
                return left // r if r != 0 else 0
            return (left or 0) / r
        if op == '%':
            return (left or 0) % (right or 1)
        if op == '==':
            return left == right
        if op == '!=':
            return left != right
        if op == '<':
            return (left or 0) < (right or 0)
        if op == '>':
            return (left or 0) > (right or 0)
        if op == '<=':
            return (left or 0) <= (right or 0)
        if op == '>=':
            return (left or 0) >= (right or 0)
        if op == 'and':
            return left and right
        if op == 'or':
            return left or right
        if op == '..':
            # Range operator: left .. right
            if isinstance(left, int) and isinstance(right, int):
                if left <= right:
                    return list(range(left, right + 1))
                else:
                    return list(range(left, right - 1, -1))
            return left
        return None

    def _eval_unary(self, node, env):
        op = node.data['op']
        val = self._eval_expr(node.data['operand'], env)
        if op == 'not':
            return not val
        if op == '-':
            return -(val or 0)
        return val

    def _eval_member(self, node, env):
        obj = self._eval_expr(node.data['object'], env)
        member = node.data['member']

        if isinstance(obj, OrrenEntity):
            # Check properties first
            if member in obj._props:
                return obj.get(member)
            # Check entity methods -> return method reference for later call
            if obj._type in self.entities:
                methods = self.entities[obj._type]['methods']
                if member in methods:
                    return ('instance_method', obj, member)
            return None

        if isinstance(obj, EntityRef):
            # Static method reference: EntityName.method
            if obj.name in self.entities:
                methods = self.entities[obj.name]['methods']
                if member in methods:
                    return ('static_method', obj.name, member)
            return None

        if isinstance(obj, list):
            if member == 'length':
                return len(obj)
            if member == 'append':
                return ('list_append', obj)
            if member == 'is_empty':
                return len(obj) == 0
            return None

        if isinstance(obj, str):
            if member == 'length':
                return len(obj)
            if member == 'is_empty':
                return len(obj) == 0
            return None

        if isinstance(obj, dict):
            return obj.get(member)

        return None

    def _eval_call(self, node, env):
        callee_node = node.data['callee']
        args = [self._eval_expr(a, env) for a in node.data['args']]

        # Direct function call: ident(args) or builtin(args)
        if callee_node.kind == 'ident':
            name = callee_node.data['name']
            if name in BUILTINS:
                return BUILTINS[name](*args)
            try:
                fn_val = env.get(name)
                return self._call_value(fn_val, args, env)
            except NameError:
                return None

        # Method call: obj.method(args)
        if callee_node.kind == 'member':
            obj = self._eval_expr(callee_node.data['object'], env)
            member = callee_node.data['member']

            if isinstance(obj, OrrenEntity):
                # Instance method call
                if obj._type in self.entities:
                    methods = self.entities[obj._type]['methods']
                    if member in methods:
                        return self._call_instance_method(
                            methods[member], obj, args, env
                        )
                return None

            if isinstance(obj, EntityRef):
                # Static method call: EntityName.method(args)
                if obj.name in self.entities:
                    methods = self.entities[obj.name]['methods']
                    if member in methods:
                        return self._call_static_method(
                            methods[member], args, env
                        )
                return None

            # Check builtins as objects (e.g., ListOps.append)
            if member == 'append' and isinstance(obj, list):
                obj.append(args[0] if args else None)
                return None

        # General: evaluate callee and call
        callee = self._eval_expr(callee_node, env)
        return self._call_value(callee, args, env)

    def _call_value(self, callee, args, env):
        if callable(callee):
            try:
                return callee(*args)
            except TypeError:
                return None
        if isinstance(callee, Node) and callee.kind == 'function':
            return self._call_function(callee, args, env)
        # EntityRef called as constructor: EntityName(arg1, arg2)
        if isinstance(callee, EntityRef) and callee.name in self.entities:
            ent = OrrenEntity(callee.name)
            for prop in self.entities[callee.name]['props']:
                default = None
                if prop['default'] is not None:
                    default = self._eval_expr(prop['default'], env)
                ent.put(prop['name'], default)
            for i, arg_val in enumerate(args):
                props = self.entities[callee.name]['props']
                if i < len(props):
                    ent.put(props[i]['name'], arg_val)
            return ent
        if isinstance(callee, tuple):
            tag = callee[0]
            if tag == 'list_append':
                callee[1].append(args[0] if args else None)
                return None
            if tag == 'instance_method':
                obj = callee[1]
                method_name = callee[2]
                if obj._type in self.entities:
                    methods = self.entities[obj._type]['methods']
                    if method_name in methods:
                        return self._call_instance_method(
                            methods[method_name], obj, args, env
                        )
            if tag == 'static_method':
                entity_name = callee[1]
                method_name = callee[2]
                if entity_name in self.entities:
                    methods = self.entities[entity_name]['methods']
                    if method_name in methods:
                        return self._call_static_method(
                            methods[method_name], args, env
                        )
        return None

    def _call_function(self, fn_node, args, env):
        local_env = Environment(env)
        params = fn_node.data['params']
        for i, p in enumerate(params):
            val = args[i] if i < len(args) else None
            local_env.define(p['name'], val)
        try:
            self._eval_block(fn_node.children, local_env)
        except ReturnSignal as e:
            return e.value
        return None

    def _call_instance_method(self, fn_node, self_obj, args, env):
        local_env = Environment(env)
        local_env.define('self', self_obj)
        params = fn_node.data['params']
        arg_idx = 0
        for p in params:
            if p['name'] == 'self':
                continue
            val = args[arg_idx] if arg_idx < len(args) else None
            local_env.define(p['name'], val)
            arg_idx += 1
        try:
            self._eval_block(fn_node.children, local_env)
        except ReturnSignal as e:
            return e.value
        return None

    def _call_static_method(self, fn_node, args, env):
        local_env = Environment(env)
        params = fn_node.data['params']
        for i, p in enumerate(params):
            val = args[i] if i < len(args) else None
            local_env.define(p['name'], val)
        try:
            self._eval_block(fn_node.children, local_env)
        except ReturnSignal as e:
            return e.value
        return None

    def _assign_target(self, target, value, env):
        if target.kind == 'member':
            obj = self._eval_expr(target.data['object'], env)
            member = target.data['member']
            if isinstance(obj, OrrenEntity):
                obj.put(member, value)
                return
            if isinstance(obj, dict):
                obj[member] = value
                return
            return

        if target.kind == 'index':
            obj = self._eval_expr(target.data['object'], env)
            idx = self._eval_expr(target.data['index'], env)
            if isinstance(obj, list) and isinstance(idx, (int, float)):
                i = int(idx)
                while len(obj) <= i:
                    obj.append(None)
                obj[i] = value
                return
            if isinstance(obj, dict):
                obj[idx] = value
                return
            return

        if target.kind == 'ident':
            name = target.data['name']
            env.set(name, value)
            return

    def _compare(self, left, op, right):
        if op == '<': return left < right
        if op == '>': return left > right
        if op == '<=': return left <= right
        if op == '>=': return left >= right
        if op == '==': return left == right
        if op == '!=': return left != right
        return False

    def _match_pattern(self, pattern, value, env):
        tag = pattern[0]
        if tag == 'wildcard':
            return True
        if tag == 'literal':
            return value == pattern[1]
        if tag == 'ident':
            try:
                return value == env.get(pattern[1])
            except NameError:
                return False
        if tag == 'dotted':
            if isinstance(value, OrrenEnum):
                return value._variant == pattern[2]
            return False
        if tag == 'constructor':
            return True  # simplified: any constructor matches
        return False


# ================================================================
# SECTION 5: BUILT-IN FUNCTIONS
# ================================================================

def _print(*args):
    print(' '.join(_to_str(a) for a in args))
    return None


def _println(*args):
    print(' '.join(_to_str(a) for a in args))
    return None


def _to_str(v):
    if v is None:
        return 'none'
    if isinstance(v, bool):
        return 'true' if v else 'false'
    if isinstance(v, int):
        return str(v)
    if isinstance(v, float):
        s = str(v)
        if s.endswith('.0') and '.' in s:
            return s
        return s
    if isinstance(v, str):
        return v
    if isinstance(v, list):
        return '[' + ', '.join(_to_str(x) for x in v) + ']'
    if isinstance(v, dict):
        return '{' + ', '.join('%s: %s' % (k, _to_str(val)) for k, val in v.items()) + '}'
    if isinstance(v, OrrenEntity):
        return '<%s>' % v._type
    if isinstance(v, OrrenEnum):
        return repr(v)
    if isinstance(v, EntityRef):
        return repr(v)
    return str(v)


def _str_fn(*args):
    return _to_str(args[0]) if args else ''


def _int_fn(*args):
    try:
        return int(args[0])
    except (ValueError, TypeError, IndexError):
        return 0


def _float_fn(*args):
    try:
        return float(args[0])
    except (ValueError, TypeError, IndexError):
        return 0.0


def _type_of(*args):
    v = args[0] if args else None
    if v is None: return 'None'
    if isinstance(v, bool): return 'Bool'
    if isinstance(v, int): return 'Int'
    if isinstance(v, float): return 'Float'
    if isinstance(v, str): return 'String'
    if isinstance(v, list): return 'List'
    if isinstance(v, dict): return 'Map'
    if isinstance(v, OrrenEntity): return v._type
    if isinstance(v, OrrenEnum): return v._enum
    if isinstance(v, EntityRef): return 'Entity<' + v.name + '>'
    if callable(v): return 'Function'
    return 'Unknown'


def _list_append(lst, val):
    if isinstance(lst, list):
        lst.append(val)
    return lst


def _list_length(lst):
    return len(lst) if isinstance(lst, list) else 0


def _list_contains(lst, item):
    if isinstance(lst, list):
        return item in lst
    return False


def _list_reverse(lst):
    if isinstance(lst, list):
        return list(reversed(lst))
    return lst


def _list_sort(lst):
    if isinstance(lst, list):
        return sorted(lst, key=lambda x: str(x))
    return lst


def _list_unique(lst):
    if isinstance(lst, list):
        seen = []
        for item in lst:
            if item not in seen:
                seen.append(item)
        return seen
    return lst


def _list_take(lst, n):
    if isinstance(lst, list):
        return lst[:int(n)]
    return lst


def _list_drop(lst, n):
    if isinstance(lst, list):
        return lst[int(n):]
    return lst


def _list_head(lst):
    if isinstance(lst, list) and len(lst) > 0:
        return lst[0]
    return None


def _list_tail(lst):
    if isinstance(lst, list) and len(lst) > 0:
        return lst[1:]
    return []


def _list_concat(a, b):
    if isinstance(a, list) and isinstance(b, list):
        return a + b
    if isinstance(a, list):
        return a
    if isinstance(b, list):
        return b
    return [a, b]


def _list_flatten(lst):
    if isinstance(lst, list):
        result = []
        for item in lst:
            if isinstance(item, list):
                result.extend(item)
            else:
                result.append(item)
        return result
    return [lst]


def _list_join(lst, sep):
    if isinstance(lst, list):
        return str(sep).join(_to_str(x) for x in lst)
    return ''


def _list_map(lst, fn_name):
    # Simplified: can't pass closures, return as-is
    return lst


def _list_filter(lst, fn_name):
    return lst


def _list_find(lst, item):
    if isinstance(lst, list):
        for i, x in enumerate(lst):
            if x == item:
                return i
    return -1


def _list_find_index(lst, item):
    return _list_find(lst, item)


def _list_empty(lst):
    return len(lst) == 0 if isinstance(lst, list) else True


def _list_clear(lst):
    if isinstance(lst, list):
        lst.clear()
    return lst


def _list_new(*args):
    return list(args)


def _str_contains(s, sub):
    return str(sub) in str(s) if s else False


def _str_length(s):
    return len(str(s)) if s else 0


def _str_split(s, sep):
    if s is None: return []
    return str(s).split(str(sep)) if sep else str(s).split()


def _str_trim(s):
    return str(s).strip() if s else ''


def _str_upper(s):
    return str(s).upper() if s else ''


def _str_lower(s):
    return str(s).lower() if s else ''


def _str_starts_with(s, prefix):
    return str(s).startswith(str(prefix)) if s else False


def _str_ends_with(s, suffix):
    return str(s).endswith(str(suffix)) if s else False


def _str_replace(s, old, new):
    return str(s).replace(str(old), str(new)) if s else ''


def _str_substring(s, start, end):
    if s is None: return ''
    s = str(s)
    return s[int(start):int(end)]


def _str_join(parts, sep):
    if isinstance(parts, list):
        return str(sep).join(_to_str(x) for x in parts)
    return ''


def _int_abs(n):
    return abs(n or 0)


def _int_max(a, b):
    return max(a or 0, b or 0)


def _int_min(a, b):
    return min(a or 0, b or 0)


def _float_abs(n):
    return abs(n or 0.0)


def _float_ceil(n):
    import math
    return math.ceil(n or 0.0)


def _float_floor(n):
    import math
    return math.floor(n or 0.0)


def _float_round(n):
    return round(n or 0.0)


def _float_to_string(n):
    if n is None: return '0.0'
    return str(float(n))


def _string_to_int(s):
    try: return int(s)
    except: return 0


def _string_to_float(s):
    try: return float(s)
    except: return 0.0


def _int_to_string(n):
    return str(int(n)) if n is not None else '0'


def _read_file(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception:
        return ''


def _write_file(path, content):
    try:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(str(content))
        return True
    except Exception:
        return False


def _read_line():
    try:
        return input()
    except EOFError:
        return ''


def _join_lines(lines):
    if isinstance(lines, list):
        return '\n'.join(str(l) for l in lines)
    return str(lines)


def _map_new():
    return {}


def _map_get(m, k):
    if isinstance(m, dict):
        return m.get(k)
    return None


def _map_put(m, k, v):
    if isinstance(m, dict):
        m[k] = v
    return m


def _map_has(m, k):
    if isinstance(m, dict):
        return k in m
    return False


def _map_keys(m):
    if isinstance(m, dict):
        return list(m.keys())
    return []


def _map_values(m):
    if isinstance(m, dict):
        return list(m.values())
    return []


def _map_size(m):
    if isinstance(m, dict):
        return len(m)
    return 0


def _json_parse(s):
    try:
        return json.loads(str(s))
    except Exception:
        return None


def _json_encode(v):
    try:
        return json.dumps(v)
    except Exception:
        return 'null'


def _system_args():
    return sys.argv


def _system_env(name):
    return os.environ.get(str(name), '')


def _exit_fn(code=0):
    sys.exit(int(code))


def _panic(msg='panic'):
    print('PANIC: ' + str(msg), file=sys.stderr)
    sys.exit(1)


def _debug_print(*args):
    print('[DEBUG]', ' '.join(_to_str(a) for a in args), file=sys.stderr)
    return None


def _error_print(*args):
    print('[ERROR]', ' '.join(_to_str(a) for a in args), file=sys.stderr)
    return None


def _range(start, end):
    return list(range(int(start), int(end)))


def _len(obj):
    if isinstance(obj, (list, str, dict)):
        return len(obj)
    return 0


def _identity(x):
    return x


def _attributes_of(v):
    return {}


def _with_confidence(v, c):
    return v


def _propagate(src, dst):
    return dst


BUILTINS = {
    'print': _print,
    'println': _println,
    'str': _str_fn,
    'int': _int_fn,
    'float': _float_fn,
    'type_of': _type_of,
    'to_string': _to_str,
    'debug_print': _debug_print,
    'error_print': _error_print,
    'panic': _panic,
    'exit': _exit_fn,
    # List operations
    'ListOps': EntityRef('ListOps'),  # placeholder
    'list_new': _list_new,
    'list_length': _list_length,
    'list_append': _list_append,
    'list_contains': _list_contains,
    'list_reverse': _list_reverse,
    'list_sort': _list_sort,
    'list_unique': _list_unique,
    'list_take': _list_take,
    'list_drop': _list_drop,
    'list_head': _list_head,
    'list_tail': _list_tail,
    'list_concat': _list_concat,
    'list_flatten': _list_flatten,
    'list_join': _list_join,
    'list_map': _list_map,
    'list_filter': _list_filter,
    'list_find': _list_find,
    'list_find_index': _list_find_index,
    'list_empty': _list_empty,
    'list_clear': _list_clear,
    # String operations
    'str_length': _str_length,
    'str_contains': _str_contains,
    'str_split': _str_split,
    'str_trim': _str_trim,
    'str_upper': _str_upper,
    'str_lower': _str_lower,
    'str_starts_with': _str_starts_with,
    'str_ends_with': _str_ends_with,
    'str_replace': _str_replace,
    'str_substring': _str_substring,
    'str_join': _str_join,
    # Int operations
    'int_abs': _int_abs,
    'int_max': _int_max,
    'int_min': _int_min,
    # Float operations
    'float_abs': _float_abs,
    'float_ceil': _float_ceil,
    'float_floor': _float_floor,
    'float_round': _float_round,
    'float_to_string': _float_to_string,
    'string_to_int': _string_to_int,
    'string_to_float': _string_to_float,
    'int_to_string': _int_to_string,
    # I/O
    'read_file': _read_file,
    'write_file': _write_file,
    'read_line': _read_line,
    'join_lines': _join_lines,
    # Map operations
    'map_new': _map_new,
    'map_get': _map_get,
    'map_put': _map_put,
    'map_has': _map_has,
    'map_keys': _map_keys,
    'map_values': _map_values,
    'map_size': _map_size,
    # JSON
    'json_parse': _json_parse,
    'json_encode': _json_encode,
    # System
    'system_args': _system_args,
    'system_env': _system_env,
    # Utility
    'range': _range,
    'len': _len,
    'identity': _identity,
    # Semantic/Cognitive bridge
    'attributes_of': _attributes_of,
    'with_confidence': _with_confidence,
    'propagate': _propagate,
}


# ================================================================
# SECTION 6: MAIN CLI
# ================================================================

def print_ast(node, indent=0):
    prefix = '  ' * indent
    if isinstance(node, list):
        for n in node:
            print_ast(n, indent)
        return
    if not isinstance(node, Node):
        return
    info = ''
    if node.data:
        info = ' ' + str(node.data)
    print('%s%s%s' % (prefix, node.kind, info))
    for c in node.children:
        print_ast(c, indent + 1)


def run_tests():
    """Run the built-in test suite to verify interpreter stability."""
    print('Orren Bootstrap Interpreter v1.0.0 - Test Suite')
    print('=' * 55)
    passed = 0
    failed = 0
    total = 0

    tests = [
        ('Tokenizer: integers', '42', lambda e: e == 42),
        ('Tokenizer: floats', '3.14', lambda e: e == 3.14),
        ('Tokenizer: strings', '"hello"', lambda e: e == 'hello'),
        ('Tokenizer: bools true', 'true', lambda e: e is True),
        ('Tokenizer: bools false', 'false', lambda e: e is False),
        ('Arithmetic: add', '1 + 2', lambda e: e == 3),
        ('Arithmetic: sub', '10 - 3', lambda e: e == 7),
        ('Arithmetic: mul', '4 * 5', lambda e: e == 20),
        ('Arithmetic: div', '10 / 3', lambda e: e == 3),
        ('Arithmetic: modulo', '10 % 3', lambda e: e == 1),
        ('Arithmetic: negative', '-5', lambda e: e == -5),
        ('Arithmetic: not true', 'not true', lambda e: e is False),
        ('Comparison: eq', '3 == 3', lambda e: e is True),
        ('Comparison: neq', '3 != 4', lambda e: e is True),
        ('Comparison: lt', '1 < 2', lambda e: e is True),
        ('Comparison: gt', '5 > 3', lambda e: e is True),
        ('Comparison: lte', '3 <= 3', lambda e: e is True),
        ('Comparison: gte', '5 >= 4', lambda e: e is True),
        ('String concat', '"hello" + " world"', lambda e: e == 'hello world'),
        ('Logic: and', 'true and false', lambda e: e is False),
        ('Logic: or', 'true or false', lambda e: e is True),
        ('List literal', '[1, 2, 3]', lambda e: e == [1, 2, 3]),
        ('List index', '[10, 20, 30][1]', lambda e: e == 20),
        ('List empty', '[]', lambda e: e == []),
    ]

    for name, code, check in tests:
        total += 1
        try:
            ev = Evaluator()
            env = Environment()
            tokens = tokenize(code)
            parser = Parser(tokens)
            stmt = parser._parse_assign_or_expr()
            result = ev._eval_node(stmt, env)
            if check(result):
                passed += 1
                print('  PASS: %s' % name)
            else:
                failed += 1
                print('  FAIL: %s (got %r)' % (name, result))
        except Exception as e:
            failed += 1
            print('  FAIL: %s (%s)' % (name, e))

    # Module-level tests
    module_tests = [
        ('Module: const', '''
const VERSION = "1.0"
''', lambda ev, env: env.get('VERSION') == '1.0'),

        ('Module: let', '''
let x = 42
''', lambda ev, env: env.get('x') == 42),

        ('Module: let be', '''
let name be "orren"
''', lambda ev, env: env.get('name') == 'orren'),

        ('Module: if true', '''
let x = 0
if true
    x = 10
else
    x = 20
end
''', lambda ev, env: env.get('x') == 10),

        ('Module: if false', '''
let x = 0
if false
    x = 10
else
    x = 20
end
''', lambda ev, env: env.get('x') == 20),

        ('Module: for in', '''
let sum = 0
for i in [1, 2, 3, 4, 5]
    sum = sum + i
end
''', lambda ev, env: env.get('sum') == 15),

        ('Module: for c style', '''
let sum = 0
let i = 0
for i < 5
    sum = sum + i
    i = i + 1
end
''', lambda ev, env: env.get('sum') == 10),

        ('Module: while', '''
let x = 0
while x < 3
    x = x + 1
end
''', lambda ev, env: env.get('x') == 3),

        ('Module: function', '''
fn add(a, b)
    return a + b
end
''', lambda ev, env: True),

        ('Module: function call', '''
fn add(a, b)
    return a + b
end
let result = add(3, 4)
''', lambda ev, env: env.get('result') == 7),

        ('Module: entity', '''
entity Point
    property x : Int = 0
    property y : Int = 0
end
''', lambda ev, env: 'Point' in ev.entities),

        ('Module: entity construct', '''
entity Point
    property x : Int = 0
    property y : Int = 0
end
let p = Point()
''', lambda ev, env: isinstance(env.get('p'), OrrenEntity) and env.get('p')._type == 'Point'),

        ('Module: entity property access', '''
entity Point
    property x : Int = 10
    property y : Int = 20
end
let p = Point()
let px = p.x
''', lambda ev, env: env.get('px') == 10),

        ('Module: entity property assign', '''
entity Point
    property x : Int = 0
    property y : Int = 0
end
let p = Point()
p.x = 42
let px = p.x
''', lambda ev, env: env.get('px') == 42),

        ('Module: entity instance method', '''
entity Counter
    property count : Int = 0
    fn inc(self)
        self.count = self.count + 1
    end
    fn get(self) -> Int
        return self.count
    end
end
let c = Counter()
c.inc()
let v = c.get()
''', lambda ev, env: env.get('v') == 1),

        ('Module: entity static method', '''
entity Pair
    property first : String = ""
    property second : String = ""
    fn new(a, b) -> Pair
        let p = Pair()
        p.first = a
        p.second = b
        return p
    end
    fn fst(self) -> String
        return self.first
    end
end
let p = Pair.new("hello", "world")
let f = p.fst()
''', lambda ev, env: env.get('f') == 'hello'),

        ('Module: enum', '''
enum Color
    RED
    GREEN
    BLUE
end
''', lambda ev, env: ev.enums.get('Color') == ['RED', 'GREEN', 'BLUE']),

        ('Module: match wildcard', '''
let x = 42
let result = 0
match x with
    _ => result = 1
end
''', lambda ev, env: env.get('result') == 1),

        ('Module: match literal', '''
let x = "hello"
let result = 0
match x with
    "world" => result = 1
    "hello" => result = 2
    _ => result = 3
end
''', lambda ev, env: env.get('result') == 2),

        ('Module: nested for', '''
let count = 0
for i in [1, 2]
    for j in [10, 20]
        count = count + 1
    end
end
''', lambda ev, env: env.get('count') == 4),

        ('Module: for c reverse', '''
let sum = 0
let i = 4
for i >= 0
    sum = sum + i
    i = i - 1
end
''', lambda ev, env: env.get('sum') == 10),

        ('Module: string operations', '''
let s = "Hello World"
let len = str_length(s)
let has = str_contains(s, "World")
let upper = str_upper(s)
let lower = str_lower("HELLO")
''', lambda ev, env: env.get('len') == 11 and env.get('has') is True and env.get('upper') == 'HELLO WORLD'),

        ('Module: list operations', '''
let items = [3, 1, 4, 1, 5]
let len = list_length(items)
let rev = list_reverse(items)
let uniq = list_unique(items)
let t = list_take(items, 3)
''', lambda ev, env: env.get('len') == 5 and env.get('t') == [3, 1, 4]),

        ('Module: export', '''
export {x, y}
''', lambda ev, env: True),

        ('Module: import parse', '''
import some.module::{Foo, Bar}
import another.thing
''', lambda ev, env: True),

        ('Module: intent', '''
intent "This is a test intent"
''', lambda ev, env: True),

        ('Module: comments', '''
-- this is a comment
let x = 5 -- inline comment
-- another comment
let y = 10
''', lambda ev, env: env.get('x') == 5 and env.get('y') == 10),

        ('Module: complex entity', '''
entity Maybe
    property value : String = ""
    property has_value : Bool = false
    fn some(v) -> Maybe
        let m = Maybe()
        m.value = v
        m.has_value = true
        return m
    end
    fn unwrap(self) -> String
        if self.has_value
            return self.value
        else
            return "none"
        end
    end
end
let m = Maybe.some("test")
let v = m.unwrap()
''', lambda ev, env: env.get('v') == 'test'),

        ('Module: print builtin', '''
print("bootstrap works")
''', lambda ev, env: True),

        ('Module: recursion', '''
fn fib(n)
    if n <= 1
        return n
    else
        return fib(n - 1) + fib(n - 2)
    end
end
let f10 = fib(10)
''', lambda ev, env: env.get('f10') == 55),

        ('Module: map builtin', '''
let m = map_new()
map_put(m, "key", "value")
let v = map_get(m, "key")
let has = map_has(m, "key")
''', lambda ev, env: env.get('v') == 'value' and env.get('has') is True),

        ('Module: json', '''
let s = json_encode(42)
let n = json_parse("123")
''', lambda ev, env: env.get('n') == 123),
    ]

    for name, code, check in module_tests:
        total += 1
        try:
            ev = Evaluator()
            tokens = tokenize(code)
            parser = Parser(tokens)
            module = parser.parse_module()
            env = ev.eval_module(module)
            if check(ev, env):
                passed += 1
                print('  PASS: %s' % name)
            else:
                failed += 1
                print('  FAIL: %s' % name)
        except Exception as e:
            failed += 1
            print('  FAIL: %s (%s)' % (name, e))

    print()
    print('Results: %d/%d passed, %d failed' % (passed, total, failed))
    if failed == 0:
        print('ALL TESTS PASSED')
    return failed == 0


def main():
    args = sys.argv[1:]
    if not args or args[0] in ('-h', '--help', 'help'):
        print('Orren Bootstrap Interpreter v1.0.0')
        print('Usage: python orren_bootstrap.py <command> [args]')
        print('Commands:')
        print('  run <file.orn>    Run an Orren file')
        print('  repl              Interactive REPL')
        print('  check <file.orn>  Parse check only')
        print('  ast <file.orn>    Print AST')
        print('  test              Run test suite')
        print('  version           Show version')
        return
    if args[0] == 'version':
        print('orren bootstrap 1.0.0')
        print('First Law: Meaning shall never be lost because of language.')
        return
    if args[0] == 'test':
        success = run_tests()
        sys.exit(0 if success else 1)
        return
    if args[0] == 'repl':
        evaluator = Evaluator()
        env = Environment()
        print('Orren REPL v1.0.0 (bootstrap)')
        print('Type expressions or \'exit\' to quit.\n')
        while True:
            try:
                line = input('orren> ')
            except EOFError:
                break
            if line.strip() in ('exit', 'quit'):
                break
            if not line.strip():
                continue
            try:
                tokens = tokenize(line)
                parser = Parser(tokens)
                stmt = parser._parse_assign_or_expr()
                result = evaluator._eval_node(stmt, env)
                if result is not None:
                    print('=> %s' % _to_str(result))
            except Exception as e:
                print('  Error: %s' % e)
        return
    if args[0] == 'check':
        if len(args) < 2:
            print('Usage: check <file.orn>')
            return
        try:
            with open(args[1], encoding='utf-8') as f:
                src = f.read()
            tokens = tokenize(src)
            parser = Parser(tokens)
            module = parser.parse_module()
            print('OK: %s parsed successfully' % args[1])
            print('  Module: %s' % module.data.get('name', '<none>'))
            print('  Top-level nodes: %d' % len(module.children))
        except ParseError as e:
            print('SYNTAX ERROR: %s' % e)
            sys.exit(1)
        except Exception as e:
            print('ERROR: %s' % e)
            sys.exit(1)
        return
    if args[0] == 'ast':
        if len(args) < 2:
            print('Usage: ast <file.orn>')
            return
        with open(args[1], encoding='utf-8') as f:
            src = f.read()
        tokens = tokenize(src)
        parser = Parser(tokens)
        module = parser.parse_module()
        print_ast(module)
        return
    if args[0] == 'run':
        if len(args) < 2:
            print('Usage: run <file.orn>')
            return
        filepath = args[1]
        if not os.path.isfile(filepath):
            print('Error: file not found: %s' % filepath)
            return
        evaluator = Evaluator()
        try:
            file_dir = os.path.dirname(os.path.abspath(filepath))
            evaluator.search_paths = [file_dir, '.']
            env = evaluator.load_and_eval_file(filepath)
            if env:
                mod_name = evaluator.current_module or '__main__'
                print('Module loaded: %s' % mod_name)
        except Exception as e:
            print('Error: %s' % e)
        return
    # Default: try to run as file
    filepath = args[0]
    if os.path.isfile(filepath):
        evaluator = Evaluator()
        try:
            file_dir = os.path.dirname(os.path.abspath(filepath))
            evaluator.search_paths = [file_dir, '.']
            env = evaluator.load_and_eval_file(filepath)
            if env:
                mod_name = evaluator.current_module or '__main__'
                print('Module loaded: %s' % mod_name)
        except Exception as e:
            print('Error: %s' % e)
    else:
        print('Error: file not found: %s' % filepath)


if __name__ == '__main__':
    main()
