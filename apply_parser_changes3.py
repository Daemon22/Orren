#!/usr/bin/env python3
"""Apply remaining parser enhancements to orren_bootstrap.py"""

path = 'bootstrap/orren_bootstrap.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

changes = 0

# === 1. Add _push_token method ===
old = """    def at(self, tt):
        return self.peek().tt == tt"""
new = """    def _push_token(self, token):
        \"\"\"Insert a token at the current position (for splitting compound tokens).\"\"\"
        self.tokens.insert(self.pos, token)

    def at(self, tt):
        return self.peek().tt == tt"""
assert old in content, '_push_token: at() method not found'
content = content.replace(old, new)
changes += 1

# === 2. Fix _parse_type: handle SHIFT_RIGHT and dotted types ===
old = """    def _parse_type(self):
        name = self._expect_ident()
        if self.at(TT.LT):
            self.advance()
            params = [self._parse_type()]
            while self.at(TT.COMMA):
                self.advance()
                self.skip_nl()
                params.append(self._parse_type())
            self.expect(TT.GT)
            return name + '<' + ','.join(params) + '>'
        return name"""
new = """    def _parse_type(self):
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
        return name"""
assert old in content, '_parse_type: original not found'
content = content.replace(old, new)
changes += 1

# === 3. Add _parse_shift and _parse_bitwise levels ===
old = """    def _parse_comparison(self):
        left = self._parse_additive()
        while self.peek().tt in (TT.EQEQ, TT.NEQ, TT.LT, TT.GT, TT.LTE, TT.GTE, TT.RANGE):
            op = self.advance().val
            right = self._parse_additive()
            left = Node('binop', data={'op': op, 'left': left, 'right': right})
        return left"""
new = """    def _parse_shift(self):
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
        return left"""
assert old in content, '_parse_comparison: original not found'
content = content.replace(old, new)
changes += 1

# === 4. Add lambda support in _parse_primary (before the IDENT handling) ===
old = """        if t.tt == TT.IDENT:
            self.advance()
            # Entity instantiation with brace syntax: Name{field=val, ...} or Name{field: val, ...}
            if self.at(TT.LBRACE):"""
new = """        # Lambda: fn a, b -> expr
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
            self.expect(TT.FAT_ARROW)
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
            if self.at(TT.LBRACE):"""
assert old in content, '_parse_primary IDENT: original not found'
content = content.replace(old, new)
changes += 1

# === 5. Fix entity construction to support list-like constructors and generic names ===
old = """                fields = {}
                if not self.at(TT.RBRACE):
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
                return Node('construct', data={'name': t.val, 'fields': fields})"""
new = """                fields = {}
                list_elements = []
                is_list_constructor = False
                if not self.at(TT.RBRACE):
                    # Check if this is a list constructor {expr, expr, ...} or entity construct {name=val, ...}
                    if t_val.tt in (TT.STRING, TT.INT, TT.FLOAT, TT.BOOL, TT.LBRACKET, TT.LBRACE, TT.LPAREN, TT.MINUS):
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
                return Node('construct', data={'name': generic_name, 'fields': fields})"""
assert old in content, 'Entity construction: original not found'
content = content.replace(old, new)
changes += 1

# Fix the reference to t_val (need to define it before the brace check)
# We need to capture the peek token before advancing
# Actually, the current code does: self.advance() then checks. We need to capture the token first.
# Let me fix by using t.val (which is the current token, since t = self.peek() at the start, and we did self.advance())
# Wait, t is the peeked token. After self.advance(), t is still the old peek. So t.tt is the IDENT's tt, not the next token's tt.
# The issue is: we need to check the FIRST token inside the braces, not t.
# Let me fix this differently - check inside the if not RBRACE block

# Replace t_val.tt with self.peek().tt in the is_list_constructor check
old = "                    if t_val.tt in (TT.STRING, TT.INT, TT.FLOAT, TT.BOOL, TT.LBRACKET, TT.LBRACE, TT.LPAREN, TT.MINUS):"
new = "                    if self.peek().tt in (TT.STRING, TT.INT, TT.FLOAT, TT.BOOL, TT.LBRACKET, TT.LBRACE, TT.LPAREN, TT.IDENT, TT.MINUS, TT.FN):"
assert old in content, 't_val reference not found'
content = content.replace(old, new)
changes += 1

# Also update the regular return to use generic_name
old = "            # For Name(args), return ident and let postfix handle () as a call\n            return Node('ident', data={'name': t.val})"
new = "            # For Name(args), return ident and let postfix handle () as a call\n            return Node('ident', data={'name': generic_name})"
assert old in content, 'ident return not found'
content = content.replace(old, new)
changes += 1

# === 6. Add tuple parsing in parenthesized expressions ===
old = """        # Map literal: Map<K,V>{k=v, ...} or just {k=v, ...}
        if t.tt == TT.LPAREN:
            self.advance()
            self.skip_nl()
            expr = self._parse_expr()
            self.skip_nl()
            self.expect(TT.RPAREN)
            return expr"""
new = """        # Parenthesized expression or tuple: (expr) or (expr, expr, ...)
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
            return first"""
assert old in content, 'Parenthesized expression: original not found'
content = content.replace(old, new)
changes += 1

# === 7. Add tuple return support in _parse_return ===
old = """    def _parse_return(self):
        self.expect(TT.RETURN)
        if self.at(TT.NEWLINE) or self.at(TT.END) or self.at(TT.EOF):
            return Node('return', data={'value': None})
        value = self._parse_expr()
        self.skip_nl()
        return Node('return', data={'value': value})"""
new = """    def _parse_return(self):
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
        return Node('return', data={'value': value})"""
assert old in content, '_parse_return: original not found'
content = content.replace(old, new)
changes += 1

# === 8. Add destructuring for-in in _parse_for ===
old = """    def _parse_for(self):
        self.expect(TT.FOR)
        if self.peek().tt != TT.IDENT:
            self.advance()
            return Node('noop')
        name = self.advance().val
        if self.at(TT.IN):"""
new = """    def _parse_for(self):
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
        # Regular for-in: for NAME in iterable do ... end
        if self.peek().tt != TT.IDENT:
            self.advance()
            return Node('noop')
        name = self.advance().val
        if self.at(TT.IN):"""
assert old in content, '_parse_for: original not found'
content = content.replace(old, new)
changes += 1

# === 9. Add skip_nl before iterable in regular for-in ===
old = """            # for X in Y [do] ... end
            self.advance()
            iterable = self._parse_expr()"""
new = """            # for X in Y [do] ... end
            self.advance()
            self.skip_nl()
            iterable = self._parse_expr()"""
assert old in content, 'for-in iterable skip_nl not found'
content = content.replace(old, new)
changes += 1

# === 10. Add skip_nl before limit in C-style for ===
old = """            limit = self._parse_expr()"""
new = """            # for var OP limit [do] ... end  (C-style with any comparison)
            # Actually this is already in the for-in path, the C-style is in else
            # Let me find the right one
            pass"""
# This might not be unique, let me skip this and use a more targeted replacement

# Actually, let me check the for-in vs for-c structure more carefully
# The for-in path has: iterable = self._parse_expr()
# The for-c path has: limit = self._parse_expr()

# === Fix the for_c limit with skip_nl ===
old_for_c = """            op = '<'
            limit = self._parse_expr()"""
new_for_c = """            op = '<'
            self.skip_nl()
            limit = self._parse_expr()"""
assert old_for_c in content, 'for-c limit not found'
content = content.replace(old_for_c, new_for_c)
changes += 1

# Undo the pass placeholder
content = content.replace(old, """            limit = self._parse_expr()""")

# === 11. Add 'let be NAME' handling ===
old = """        # Handle: let mut NAME (or let be NAME) - optional mut/be after let
        is_mut = False
        if self.at(TT.MUT):
            is_mut = True
            self.advance()
        # Handle: let self.x = value (property assignment)
        if self.at(TT.SELF):"""
new = """        # Handle: let mut NAME or let be NAME - optional keywords after let
        is_mut = False
        if self.at(TT.MUT):
            is_mut = True
            self.advance()
        elif self.at(TT.BE) and len(self.tokens) > self.pos + 1 and self.tokens[self.pos + 1].tt in (TT.IDENT,):
            # 'let be NAME = value' - 'be' is a binding keyword, not the variable name
            self.advance()
        # Handle: let self.x = value (property assignment)
        if self.at(TT.SELF):"""
assert old in content, '_parse_let: let be handling not found'
content = content.replace(old, new)
changes += 1

# === 12. Handle skip_nl after skip_brace for while and match (already done in batch 1?) ===
# The _parse_while doesn't have skip_nl after WHILE
old = """    def _parse_while(self):
        self.expect(TT.WHILE)
        condition = self._parse_expr()"""
new = """    def _parse_while(self):
        self.expect(TT.WHILE)
        self.skip_nl()
        condition = self._parse_expr()"""
assert old in content, '_parse_while skip_nl not found'
content = content.replace(old, new)
changes += 1

# === 13. Handle skip_nl in _parse_match ===
old = """    def _parse_match(self):
        self.expect(TT.MATCH)
        expr = self._parse_expr()
        self.expect(TT.WITH)"""
new = """    def _parse_match(self):
        self.expect(TT.MATCH)
        self.skip_nl()
        expr = self._parse_expr()
        self.skip_nl()
        self.expect(TT.WITH)"""
assert old in content, '_parse_match skip_nl not found'
content = content.replace(old, new)
changes += 1

# === 14. Handle skip_nl in _parse_match_as_expr ===
old = """    def _parse_match_as_expr(self):
        \"\"\"Parse a match expression used as a sub-expression.\"\"\"
        self.expect(TT.MATCH)
        expr = self._parse_expr()
        self.expect(TT.WITH)"""
new = """    def _parse_match_as_expr(self):
        \"\"\"Parse a match expression used as a sub-expression.\"\"\"
        self.expect(TT.MATCH)
        self.skip_nl()
        expr = self._parse_expr()
        self.skip_nl()
        self.expect(TT.WITH)"""
assert old in content, '_parse_match_as_expr skip_nl not found'
content = content.replace(old, new)
changes += 1

# === 15. Handle skip_nl in _parse_assign_or_expr after assignment ===
old = """    def _parse_assign_or_expr(self):
        expr = self._parse_expr()
        self.skip_nl()
        if self.at(TT.EQ):"""
new = """    def _parse_assign_or_expr(self):
        expr = self._parse_expr()
        self.skip_nl()
        if self.at(TT.EQ):
            self.advance()
            self.skip_nl()
            value = self._parse_assign_or_expr()
            return Node('assign', data={'target': expr, 'value': value})
        return expr"""
assert old in content, '_parse_assign_or_expr structure not found'
content = content.replace(old, new)
changes += 1

# === 16: Handle 'do' on new line for if expressions ===
# Check if _parse_if already handles this - it should with skip_nl

# === 17: Handle import module.{X, Y} (dot-brace imports) ===
old = """        # import from a.b.c::{X, Y}
        elif self.at(TT.IDENT):
            path = [self._expect_ident()]
            if self.at(TT.DOT):
                self.advance()
                path.append(self._expect_ident())
                if self.at(TT.DOT):
                    self.advance()
                    path.append(self._expect_ident())
            # Check for ::{X, Y} or .{X, Y}
            if self.at(TT.COLON):
                self.advance()
                if self.at(TT.COLON):
                    self.advance()
                    if self.at(TT.LBRACE):
                        self.advance()
                        self.skip_nl()
                        names = []
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
                        return Node('import', data={'path': '.'.join(path), 'names': names})
            return Node('import', data={'path': '.'.join(path), 'names': []})"""
new = """        # import from a.b.c::{X, Y} or a.b.c.{X, Y}
        elif self.at(TT.IDENT):
            path = [self._expect_ident()]
            if self.at(TT.DOT):
                self.advance()
                path.append(self._expect_ident())
                if self.at(TT.DOT):
                    self.advance()
                    path.append(self._expect_ident())
            # Check for ::{X, Y} or .{X, Y}
            if self.at(TT.COLON):
                self.advance()
                if self.at(TT.COLON):
                    self.advance()
                    if self.at(TT.LBRACE):
                        self.advance()
                        self.skip_nl()
                        names = []
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
                        return Node('import', data={'path': '.'.join(path), 'names': names})
            elif self.at(TT.DOT):
                self.advance()
                if self.at(TT.LBRACE):
                    self.advance()
                    self.skip_nl()
                    names = []
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
                    return Node('import', data={'path': '.'.join(path), 'names': names})
            return Node('import', data={'path': '.'.join(path), 'names': []})"""
assert old in content, 'Import dot-brace not found'
content = content.replace(old, new)
changes += 1

print(f'Total changes applied: {changes}')

with open('bootstrap/orren_bootstrap.py', 'w', encoding='utf-8') as f:
    f.write(content)

print(f'File written. Total lines: {len(content.split(chr(10)))}')
