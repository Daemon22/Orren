#!/usr/bin/env python3
"""Apply ALL parser enhancements to orren_bootstrap.py - comprehensive version."""
import sys

path = 'bootstrap/orren_bootstrap.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

applied = 0
failed = 0

def try_replace(old, new, label):
    global content, applied, failed
    if old in content:
        content = content.replace(old, new, 1)
        applied += 1
        print(f'  APPLIED: {label}')
    else:
        failed += 1
        print(f'  SKIP (not found): {label}')

# === 1. _push_token method ===
try_replace(
    """    def at(self, tt):
        return self.peek().tt == tt""",
    """    def _push_token(self, token):
        \"\"\"Insert a token at the current position (for splitting compound tokens).\"\"\"
        self.tokens.insert(self.pos, token)

    def at(self, tt):
        return self.peek().tt == tt""",
    '1. _push_token method')

# === 2. _parse_type: SHIFT_RIGHT split + dotted types ===
try_replace(
    """    def _parse_type(self):
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
        return name""",
    """    def _parse_type(self):
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
        return name""",
    '2. _parse_type SHIFT_RIGHT + dotted types')

# === 3. Add _parse_shift and _parse_bitwise, fix _parse_comparison ===
try_replace(
    """    def _parse_comparison(self):
        left = self._parse_additive()
        while self.peek().tt in (TT.EQEQ, TT.NEQ, TT.LT, TT.GT, TT.LTE, TT.GTE, TT.RANGE):
            op = self.advance().val
            right = self._parse_additive()
            left = Node('binop', data={'op': op, 'left': left, 'right': right})
        return left""",
    """    def _parse_shift(self):
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
        return left""",
    '3. _parse_shift + _parse_bitwise + comparison fix')

# === 4. Lambda + generic type in _parse_primary ===
try_replace(
    """        if t.tt == TT.IDENT:
            self.advance()
            # Entity instantiation with brace syntax: Name{field=val, ...} or Name{field: val, ...}
            if self.at(TT.LBRACE):""",
    """        # Lambda: fn a, b -> expr
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
            if self.at(TT.LBRACE):""",
    '4. Lambda + generic type in _parse_primary')

# === 5. List-like entity construction + generic_name ===
try_replace(
    """                fields = {}
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
                return Node('construct', data={'name': t.val, 'fields': fields})""",
    """                fields = {}
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
                return Node('construct', data={'name': generic_name, 'fields': fields})""",
    '5. List-like entity construction + generic_name')

# === 6. Update ident return to use generic_name ===
try_replace(
    """            # For Name(args), return ident and let postfix handle () as a call
            return Node('ident', data={'name': t.val})""",
    """            # For Name(args), return ident and let postfix handle () as a call
            return Node('ident', data={'name': generic_name})""",
    '6. ident return uses generic_name')

# === 7. Tuple parsing in parenthesized expressions ===
try_replace(
    """        # Map literal: Map<K,V>{k=v, ...} or just {k=v, ...}
        if t.tt == TT.LPAREN:
            self.advance()
            self.skip_nl()
            expr = self._parse_expr()
            self.skip_nl()
            self.expect(TT.RPAREN)
            return expr""",
    """        # Parenthesized expression or tuple: (expr) or (expr, expr, ...)
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
            return first""",
    '7. Tuple parsing in parenthesized expressions')

# === 8. Tuple return support in _parse_return ===
try_replace(
    """    def _parse_return(self):
        self.expect(TT.RETURN)
        if self.at(TT.NEWLINE) or self.at(TT.END) or self.at(TT.EOF):
            return Node('return', data={'value': None})
        value = self._parse_expr()
        self.skip_nl()
        return Node('return', data={'value': value})""",
    """    def _parse_return(self):
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
        return Node('return', data={'value': value})""",
    '8. Tuple return support')

# === 9. Destructuring for-in ===
try_replace(
    """    def _parse_for(self):
        self.expect(TT.FOR)
        if self.peek().tt != TT.IDENT:""",
    """    def _parse_for(self):
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
        if self.peek().tt != TT.IDENT:""",
    '9. Destructuring for-in')

# === 10. skip_nl before for-in iterable ===
try_replace(
    """            # for X in Y [do] ... end
            self.advance()
            iterable = self._parse_expr()""",
    """            # for X in Y [do] ... end
            self.advance()
            self.skip_nl()
            iterable = self._parse_expr()""",
    '10. for-in iterable skip_nl')

# === 11. skip_nl before for-c limit ===
try_replace(
    """            else:
                op = '<'
            limit = self._parse_expr()""",
    """            else:
                op = '<'
            self.skip_nl()
            limit = self._parse_expr()""",
    '11. for-c limit skip_nl')

# === 12. 'let be NAME' handling ===
try_replace(
    """        # Handle: let mut NAME (or let be NAME) - optional mut/be after let
        is_mut = False
        if self.at(TT.MUT):
            is_mut = True
            self.advance()
        # Handle: let self.x = value (property assignment)""",
    """        # Handle: let mut NAME or let be NAME - optional keywords after let
        is_mut = False
        if self.at(TT.MUT):
            is_mut = True
            self.advance()
        elif self.at(TT.BE) and len(self.tokens) > self.pos + 1 and self.tokens[self.pos + 1].tt in (TT.IDENT,):
            # 'let be NAME = value' - 'be' is a binding keyword, not the variable name
            self.advance()
        # Handle: let self.x = value (property assignment)""",
    '12. let be NAME handling')

# === 13. skip_nl after WHILE ===
try_replace(
    """    def _parse_while(self):
        self.expect(TT.WHILE)
        condition = self._parse_expr()""",
    """    def _parse_while(self):
        self.expect(TT.WHILE)
        self.skip_nl()
        condition = self._parse_expr()""",
    '13. skip_nl after WHILE')

# === 14. skip_nl after MATCH and before WITH ===
try_replace(
    """    def _parse_match(self):
        self.expect(TT.MATCH)
        expr = self._parse_expr()
        self.expect(TT.WITH)""",
    """    def _parse_match(self):
        self.expect(TT.MATCH)
        self.skip_nl()
        expr = self._parse_expr()
        self.skip_nl()
        self.expect(TT.WITH)""",
    '14. skip_nl in _parse_match')

# === 15. skip_nl in _parse_match_as_expr ===
try_replace(
    """    def _parse_match_as_expr(self):
        \"\"\"Parse a match expression used as a sub-expression.\"\"\"
        self.expect(TT.MATCH)
        expr = self._parse_expr()
        self.expect(TT.WITH)""",
    """    def _parse_match_as_expr(self):
        \"\"\"Parse a match expression used as a sub-expression.\"\"\"
        self.expect(TT.MATCH)
        self.skip_nl()
        expr = self._parse_expr()
        self.skip_nl()
        self.expect(TT.WITH)""",
    '15. skip_nl in _parse_match_as_expr')

# === 16. Fix _parse_assign_or_expr to add skip_nl after _parse_expr ===
try_replace(
    """    def _parse_assign_or_expr(self):
        expr = self._parse_expr()
        if self.at(TT.EQ):
            self.advance()
            value = self._parse_expr()
            self.skip_nl()
            return Node('assign', data={'target': expr, 'value': value})
        self.skip_nl()
        return Node('expr_stmt', data={'expr': expr})""",
    """    def _parse_assign_or_expr(self):
        expr = self._parse_expr()
        self.skip_nl()
        if self.at(TT.EQ):
            self.advance()
            self.skip_nl()
            value = self._parse_assign_or_expr()
            return Node('assign', data={'target': expr, 'value': value})
        self.skip_nl()
        return Node('expr_stmt', data={'expr': expr})""",
    '16. _parse_assign_or_expr skip_nl')

# === 17. skip_nl after IF in _parse_if ===
try_replace(
    """    def _parse_if(self):
        self.expect(TT.IF)
        condition = self._parse_expr()""",
    """    def _parse_if(self):
        self.expect(TT.IF)
        self.skip_nl()
        condition = self._parse_expr()""",
    '17. skip_nl after IF')

# === 18. skip_nl after FOR in _parse_for for-in iterable ===
# Already handled by #10

# === 19. skip_nl in const value parsing ===
try_replace(
    """        self.expect(TT.EQ)
        value = self._parse_expr()""",
    """        self.expect(TT.EQ)
        self.skip_nl()
        value = self._parse_expr()""",
    '19. skip_nl in const value')

# === 20. skip_nl in property default ===
try_replace(
    """                if self.at(TT.EQ):
                    self.advance()
                    default = self._parse_expr()""",
    """                if self.at(TT.EQ):
                    self.advance()
                    self.skip_nl()
                    default = self._parse_expr()""",
    '20. skip_nl in property default')

# === 21. skip_nl in self.x let value ===
try_replace(
    """                if self.at(TT.BE) or self.at(TT.EQ):
                    self.advance()
                    value = self._parse_assign_or_expr()""",
    """                if self.at(TT.BE) or self.at(TT.EQ):
                    self.advance()
                    self.skip_nl()
                    value = self._parse_assign_or_expr()""",
    '21. skip_nl in self.x let value')

# === 22. skip_nl after do in _parse_for for-in ===
try_replace(
    """            if self.at(TT.DO):
                self.advance()
                self.skip_nl()
            body = self._parse_block()
            self.expect(TT.END)
            self.skip_nl()
            return Node('for_in', data={'var': name, 'iterable': iterable}, children=body)""",
    """            if self.at(TT.DO):
                self.advance()
                self.skip_nl()
            body = self._parse_block()
            self.expect(TT.END)
            self.skip_nl()
            return Node('for_in', data={'var': name, 'iterable': iterable, 'destructure': None}, children=body)""",
    '22. Add destructure: None to for_in return')

# === 23. skip_nl after do in for-c ===
try_replace(
    """            if self.at(TT.DO):
                self.advance()
                self.skip_nl()
            body = self._parse_block()
            self.expect(TT.END)
            self.skip_nl()
            return Node('for_c', data={'var': name, 'op': op, 'limit': limit}, children=body)""",
    """            if self.at(TT.DO):
                self.advance()
                self.skip_nl()
            body = self._parse_block()
            self.expect(TT.END)
            self.skip_nl()
            return Node('for_c', data={'var': name, 'op': op, 'limit': limit, 'destructure': None}, children=body)""",
    '23. Add destructure: None to for_c return')

# === 24. skip_nl after do in _parse_while ===
try_replace(
    """    def _parse_while(self):
        self.expect(TT.WHILE)
        self.skip_nl()
        condition = self._parse_expr()
        self.skip_nl()
        if self.at(TT.DO):
            self.advance()
            self.skip_nl()
        body = self._parse_block()""",
    """    def _parse_while(self):
        self.expect(TT.WHILE)
        self.skip_nl()
        condition = self._parse_expr()
        self.skip_nl()
        if self.at(TT.DO):
            self.advance()
            self.skip_nl()
        body = self._parse_block()""",
    '24. Verify _parse_while already has skip_nl (no-op if already applied)')

# === 25. Handle 'let be NAME: Type = value' ===
# The current _parse_let after the let mut/be handling:
# name = self._expect_ident()
# type_ann = ... (handles COLON)
# This should work for 'let be NAME: Type = value'

# === 26: Handle 'then' after if condition (already supported) ===

# === 27: Handle skip_nl in _parse_if else-if chain ===
try_replace(
    """            if self.at(TT.IF):
                self.advance()
                econd = self._parse_expr()
                self.skip_nl()""",
    """            if self.at(TT.IF):
                self.advance()
                self.skip_nl()
                econd = self._parse_expr()
                self.skip_nl()""",
    '27. skip_nl in else-if chain')

# === 28: Handle 'let be NAME = []' - the value is a list literal ===
# The current _parse_assign_or_expr calls _parse_expr which handles [list]
# And depth-aware newlines should handle [] across lines

# === 29: Handle skip_nl in _parse_statement return ===
# The _parse_statement already calls _parse_assign_or_expr which handles everything

print(f'\nApplied: {applied}, Skipped: {failed}')

with open('bootstrap/orren_bootstrap.py', 'w', encoding='utf-8') as f:
    f.write(content)

print(f'File written. Total lines: {len(content.split(chr(10)))}')
