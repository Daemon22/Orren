#!/usr/bin/env python3
"""Apply parser enhancements to orren_bootstrap.py"""
import sys

path = 'bootstrap/orren_bootstrap.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

changes = 0

# === Change 1: Add MUT and operator token types to TT class ===
old = """    TRUE = 'TRUE'
    FALSE = 'FALSE'
    CASE = 'CASE'
    # Operators"""
new = """    TRUE = 'TRUE'
    FALSE = 'FALSE'
    CASE = 'CASE'
    MUT = 'MUT'
    # Operators"""
assert old in content, 'TT: TRUE/CASE block not found'
content = content.replace(old, new)
changes += 1

old = "    RANGE = 'RANGE'          # .."
new = """    RANGE = 'RANGE'          # ..
    SHIFT_LEFT = 'SHIFT_LEFT'  # <<
    SHIFT_RIGHT = 'SHIFT_RIGHT'  # >>
    BIT_AND = 'BIT_AND'      # &
    BIT_XOR = 'BIT_XOR'       # ^"""
assert old in content, 'TT: RANGE not found'
content = content.replace(old, new)
changes += 1

# === Change 2: Add 'mut' to KEYWORDS ===
old = "    'as': TT.AS,"
new = "    'as': TT.AS, 'mut': TT.MUT,"
assert old in content, 'KEYWORDS: AS not found'
content = content.replace(old, new)
changes += 1

# === Change 3: Add & and ^ to SINGLE_CHARS ===
old = """    '(': TT.LPAREN, ')': TT.RPAREN, '{': TT.LBRACE,
    '}': TT.RBRACE, '[': TT.LBRACKET, ']': TT.RBRACKET,
    '#': TT.HASH,
}"""
new = """    '(': TT.LPAREN, ')': TT.RPAREN, '{': TT.LBRACE,
    '}': TT.RBRACE, '[': TT.LBRACKET, ']': TT.RBRACKET,
    '#': TT.HASH,
    '&': TT.BIT_AND,
    '^': TT.BIT_XOR,
}"""
assert old in content, 'SINGLE_CHARS not found'
content = content.replace(old, new)
changes += 1

# === Change 4: Add << and >> to tokenizer ===
old = "        # Two-char range operator: .."
new = """        # Two-char shift operators: << and >>
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

        # Two-char range operator: .."""
assert old in content, 'Range operator not found'
content = content.replace(old, new)
changes += 1

# === Change 5: Depth-aware newline suppression in tokenizer ===
old = """    tokens = []
    i = 0
    line = 1
    col = 1
    n = len(source)"""
new = """    tokens = []
    i = 0
    line = 1
    col = 1
    n = len(source)
    depth = 0  # Track nesting of (), [], {} to suppress newlines inside"""
assert old in content, 'tokenize init not found'
content = content.replace(old, new, 1)
changes += 1

# Modify newline handling
old = """        # Newlines
        if c == '\\n':
            if tokens and tokens[-1].tt != TT.NEWLINE:
                tokens.append(Token(TT.NEWLINE, '\\\\n', line, col))
            line += 1
            col = 1
            i += 1
            continue"""
new = """        # Newlines (suppressed inside (), [], {} to allow multi-line expressions)
        if c == '\\n':
            if depth == 0:
                if tokens and tokens[-1].tt != TT.NEWLINE:
                    tokens.append(Token(TT.NEWLINE, '\\\\n', line, col))
            line += 1
            col = 1
            i += 1
            continue"""
assert old in content, 'Newline handling not found'
content = content.replace(old, new)
changes += 1

# Add depth tracking around single-char operators
old = """        # Single-char operators
        if c in SINGLE_CHARS:
            tokens.append(Token(SINGLE_CHARS[c], c, line, col))
            i += 1
            col += 1
            continue"""
new = """        # Single-char operators
        if c in SINGLE_CHARS:
            if c in '([{':
                depth += 1
            elif c in ')]}':
                depth -= 1
            tokens.append(Token(SINGLE_CHARS[c], c, line, col))
            i += 1
            col += 1
            continue"""
assert old in content, 'Single-char operators not found'
content = content.replace(old, new)
changes += 1

print(f'Tokenizer changes applied: {changes}')

# === Change 6: Fix and/or precedence ===
# Remove AND from multiplicative and OR from additive
old = """    def _parse_additive(self):
        left = self._parse_multiplicative()
        while self.peek().tt in (TT.PLUS, TT.MINUS, TT.OR):
            op = self.advance().val
            right = self._parse_multiplicative()
            left = Node('binop', data={'op': op, 'left': left, 'right': right})
        return left

    def _parse_multiplicative(self):
        left = self._parse_unary()
        while self.peek().tt in (TT.STAR, TT.SLASH, TT.PERCENT, TT.AND):
            op = self.advance().val
            right = self._parse_unary()
            left = Node('binop', data={'op': op, 'left': left, 'right': right})
        return left"""
new = """    def _parse_additive(self):
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
        return left"""
assert old in content, 'Expression precedence methods not found'
content = content.replace(old, new)
changes += 1

# Update _parse_expr to use _parse_logical_or
old = """    def _parse_expr(self, min_prec=0):
        return self._parse_comparison()"""
new = """    def _parse_expr(self, min_prec=0):
        return self._parse_logical_or()"""
assert old in content, '_parse_expr not found'
content = content.replace(old, new)
changes += 1

# === Change 7: Fix _parse_comparison to use _parse_additive properly ===
# (Already done above - _parse_logical_and calls _parse_comparison which calls _parse_additive)

# === Change 8: Support 'let be NAME' and 'let mut NAME' ===
old = """    def _parse_let(self):
        self.expect(TT.LET)
        # Handle: let self.x = value (property assignment)
        if self.at(TT.SELF):"""
new = """    def _parse_let(self):
        self.expect(TT.LET)
        # Handle: let mut NAME (or let be NAME) - optional mut/be after let
        is_mut = False
        if self.at(TT.MUT):
            is_mut = True
            self.advance()
        # Handle: let self.x = value (property assignment)
        if self.at(TT.SELF):"""
assert old in content, '_parse_let start not found'
content = content.replace(old, new)
changes += 1

# Fix the let node to include is_mut
old = """        self.skip_nl()
        return Node('let', data={'name': name, 'type': type_ann, 'value': value})"""
new = """        self.skip_nl()
        return Node('let', data={'name': name, 'type': type_ann, 'value': value, 'is_mut': is_mut})"""
assert old in content, '_parse_let return not found'
content = content.replace(old, new)  # This is in the self.x branch
content = content.replace(old, new)  # This is in the regular branch - wait, both have same return
# Actually we need to be more careful. Let me check.
changes += 1

# Fix value parsing to use _parse_assign_or_expr
old = """        value = None
        if self.at(TT.BE):
            self.advance()
            value = self._parse_expr()
        elif self.at(TT.EQ):
            self.advance()
            value = self._parse_expr()
        self.skip_nl()
        return Node('let', data={'name': name, 'type': type_ann, 'value': value, 'is_mut': is_mut})"""
new = """        value = None
        if self.at(TT.BE):
            self.advance()
            value = self._parse_assign_or_expr()
        elif self.at(TT.EQ):
            self.advance()
            value = self._parse_assign_or_expr()
        self.skip_nl()
        return Node('let', data={'name': name, 'type': type_ann, 'value': value, 'is_mut': is_mut})"""
assert old in content, '_parse_let value parsing not found'
content = content.replace(old, new)
changes += 1

# Also fix the self.x branch to use _parse_assign_or_expr
old = """                if self.at(TT.BE) or self.at(TT.EQ):
                    self.advance()
                    value = self._parse_expr()
                else:
                    value = None"""
new = """                if self.at(TT.BE) or self.at(TT.EQ):
                    self.advance()
                    value = self._parse_assign_or_expr()
                else:
                    value = None"""
assert old in content, 'self.x let branch not found'
content = content.replace(old, new)
changes += 1

print(f'Total changes applied: {changes}')
print('Writing file...')

with open('bootstrap/orren_bootstrap.py', 'w', encoding='utf-8') as f:
    f.write(content)

print(f'File written. Total lines: {len(content.split(chr(10)))}')
