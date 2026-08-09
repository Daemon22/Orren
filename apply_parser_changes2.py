#!/usr/bin/env python3
"""Apply comprehensive parser enhancements to orren_bootstrap.py"""
import re

path = 'bootstrap/orren_bootstrap.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

changes = 0

# === Fix 1: Remove >> from tokenizer (handle in parser instead) ===
# Replace the >> handling to not combine the tokens
old = """        # Two-char range operator: .."""
new = """        # Two-char shift operator: <<
        if source[i:i + 2] == '<<':
            tokens.append(Token(TT.SHIFT_LEFT, '<<', line, col))
            i += 2
            col += 2
            continue

        # Two-char range operator: .."""
assert old in content, 'Range operator comment not found'
content = content.replace(old, new, 1)
changes += 1

# Remove the >> handling (replace SHIFT_RIGHT block with nothing - actually we need to handle >> as shift in the parser)
# Actually, we keep SHIFT_RIGHT in the tokenizer but handle the split in _parse_type
# But we ALSO need to handle >> in expression context (shift right)
# Let me keep the >> handling and fix _parse_type to split it

# === Fix 2: Add _push_token method to Parser class ===
old = """    def skip_nl(self):
        while self.peek().tt == TT.NEWLINE:
            self.advance()

    def at(self, tt):
        return self.peek().tt == tt"""
new = """    def skip_nl(self):
        while self.peek().tt == TT.NEWLINE:
            self.advance()

    def _push_token(self, token):
        \"\"\"Insert a token at the current position (for splitting compound tokens).\"\"\"
        self.tokens.insert(self.pos, token)

    def at(self, tt):
        return self.peek().tt == tt"""
assert old in content, 'skip_nl/at method not found'
content = content.replace(old, new)
changes += 1

# === Fix 3: Fix _parse_type to handle SHIFT_RIGHT and dotted names ===
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
assert old in content, '_parse_type not found'
content = content.replace(old, new)
changes += 1

# === Fix 4: Add shift and bitwise levels to expression parsing ===
# Insert new methods after _parse_additive and before _parse_multiplicative
old = """    def _parse_multiplicative(self):
        left = self._parse_unary()
        while self.peek().tt in (TT.STAR, TT.SLASH, TT.PERCENT, TT.AND):
            op = self.advance().val
            right = self._parse_unary()
            left = Node('binop', data={'op': op, 'left': left, 'right': right})
        return left"""
new = """    def _parse_multiplicative(self):
        left = self._parse_unary()
        while self.peek().tt in (TT.STAR, TT.SLASH, TT.PERCENT):
            op = self.advance().val
            right = self._parse_unary()
            left = Node('binop', data={'op': op, 'left': left, 'right': right})
        return left

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
        return left"""
assert old in content, '_parse_multiplicative not found'
content = content.replace(old, new)
changes += 1

# Update _parse_comparison to use _parse_bitwise instead of _parse_additive
old = """    def _parse_comparison(self):
        left = self._parse_additive()
        while self.peek().tt in (TT.EQEQ, TT.NEQ, TT.LT, TT.GT, TT.LTE, TT.GTE, TT.RANGE):
            op = self.advance().val
            right = self._parse_additive()
            left = Node('binop', data={'op': op, 'left': left, 'right': right})
        return left"""
new = """    def _parse_comparison(self):
        left = self._parse_bitwise()
        while self.peek().tt in (TT.EQEQ, TT.NEQ, TT.LT, TT.GT, TT.LTE, TT.GTE, TT.RANGE):
            op = self.advance().val
            right = self._parse_bitwise()
            left = Node('binop', data={'op': op, 'left': left, 'right': right})
        return left"""
assert old in content, '_parse_comparison not found'
content = content.replace(old, new)
changes += 1

# === Fix 5: Add generic type support in _parse_primary ===
# This handles List<String>(), List<String>{}, List<String>.method(), Map<K,V>{...}
old = """        if t.tt == TT.IDENT:
            self.advance()
            # Entity instantiation with brace syntax: Name{field=val, ...} or Name{field: val, ...}
            if self.at(TT.LBRACE):"""
new = """        if t.tt == TT.IDENT:
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
            # Also handles List<Type>{expr, expr, ...} for list constructors
            if self.at(TT.LBRACE):"""
assert old in content, 'Primary IDENT handling not found'
content = content.replace(old, new)
changes += 1

# Now update the construct node to use generic_name instead of t.val
old = """                self.expect(TT.RBRACE)
                return Node('construct', data={'name': t.val, 'fields': fields})
            # For Name(args), return ident and let postfix handle () as a call
            return Node('ident', data={'name': t.val})"""
new = """                self.expect(TT.RBRACE)
                return Node('construct', data={'name': generic_name, 'fields': fields})
            # For Name(args), return ident and let postfix handle () as a call
            return Node('ident', data={'name': generic_name})"""
assert old in content, 'construct return not found'
content = content.replace(old, new)
changes += 1

# === Fix 6: Handle list-like entity construction {expr, expr, ...} ===
# When entity construction gets a STRING or non-ident first element, treat as list/tuple constructor
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
                return Node('construct', data={'name': generic_name, 'fields': fields})"""
new = """                fields = {}
                list_elements = []
                is_list_constructor = False
                if not self.at(TT.RBRACE):
                    # Check if this is a list constructor {expr, expr, ...} or entity construct {name=val, ...}
                    if self.at(TT.STRING) or self.at(TT.INT) or self.at(TT.FLOAT) or self.at(TT.BOOL) or self.at(TT.LBRACKET) or self.at(TT.LBRACE) or self.at(TT.LPAREN):
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
assert old in content, 'entity construction fields not found'
content = content.replace(old, new)
changes += 1

# === Fix 7: Add tuple return support in _parse_return ===
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
            # Tuple return: return (a, b, c)
            if self.at(TT.RPAREN) or self.at(TT.NEWLINE):
                self.skip_nl()
                if self.at(TT.COMMA):
                    elements = []
                    while self.at(TT.COMMA):
                        self.advance()
                        self.skip_nl()
                        if self.at(TT.RPAREN):
                            break
                        elements.append(self._parse_expr())
                    self.skip_nl()
                    self.expect(TT.RPAREN)
                    return Node('return', data={'value': Node('tuple', data={'elements': elements})})
                self.expect(TT.RPAREN)
                return Node('return', data={'value': None})
            # Single parenthesized expression or tuple
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
assert old in content, '_parse_return not found'
content = content.replace(old, new)
changes += 1

# === Fix 8: Add lambda support in _parse_primary ===
# Handle fn a, b -> expr  (anonymous function)
old = """        # Map literal: Map<K,V>{k=v, ...} or just {k=v, ...}
        if t.tt == TT.LPAREN:
            self.advance()
            self.skip_nl()
            expr = self._parse_expr()
            self.skip_nl()
            self.expect(TT.RPAREN)
            return expr"""
new = """        # Lambda: fn a, b -> expr  or  fn a, b -> a + b
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
            # Parse single expression body (no do/end)
            body_expr = self._parse_expr()
            self.skip_nl()
            return Node('lambda', data={'params': params, 'body': body_expr})

        # Parenthesized expression or tuple
        if t.tt == TT.LPAREN:"""
assert old in content, 'Primary LPAREN/map literal not found'
content = content.replace(old, new)
changes += 1

# Update the LPAREN handling to also handle tuples
old = """        # Parenthesized expression or tuple
        if t.tt == TT.LPAREN:
            self.advance()
            self.skip_nl()
            expr = self._parse_expr()
            self.skip_nl()
            self.expect(TT.RPAREN)
            return expr"""
new = """        # Parenthesized expression or tuple
        if t.tt == TT.LPAREN:
            self.advance()
            self.skip_nl()
            # Handle empty parens () - could be empty tuple or unit
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
assert old in content, 'Parenthesized expression not found'
content = content.replace(old, new)
changes += 1

# === Fix 9: Add skip_nl in _parse_function for multi-line params ===
old = """        if not self.at(TT.RPAREN):
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
                params.append(p)"""
new = """        if not self.at(TT.RPAREN):
            self.skip_nl()
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
                    params.append(p)"""
assert old in content, 'Function params parsing not found'
content = content.replace(old, new)
changes += 1

# Add skip_nl before RPAREN expectation in function
old = """        self.expect(TT.RPAREN)
        ret_type = None
        if self.at(TT.ARROW):
            self.advance()
            ret_type = self._parse_type()
        self.skip_nl()
        if self.at(TT.DO):"""
new = """        self.skip_nl()
        self.expect(TT.RPAREN)
        ret_type = None
        if self.at(TT.ARROW):
            self.advance()
            ret_type = self._parse_type()
        self.skip_nl()
        if self.at(TT.DO):"""
assert old in content, 'Function return type parsing not found'
content = content.replace(old, new)
changes += 1

# === Fix 10: Handle 'do' on next line after function params ===
# Already handled by skip_nl above

# === Fix 11: Add dotted type name and generic support in _parse_param ===
old = """    def _parse_param(self):
        name = self._expect_ident()
        type_ann = None
        if self.at(TT.COLON):
            self.advance()
            type_ann = self._parse_type()
        return {'name': name, 'type': type_ann}"""
new = """    def _parse_param(self):
        name = self._expect_ident()
        type_ann = None
        if self.at(TT.COLON):
            self.advance()
            type_ann = self._parse_type()
        # Also handle -> as return type arrow for params (lambda params)
        return {'name': name, 'type': type_ann}"""
assert old in content, '_parse_param not found'
content = content.replace(old, new)
changes += 1

# === Fix 12: Handle 'if (condition) then' ===
old = """    def _parse_if(self):
        self.expect(TT.IF)
        condition = self._parse_expr()
        self.skip_nl()
        if self.at(TT.THEN):
            self.advance()
        self.skip_nl()
        then_body = self._parse_block()"""
new = """    def _parse_if(self):
        self.expect(TT.IF)
        self.skip_nl()
        condition = self._parse_expr()
        self.skip_nl()
        if self.at(TT.THEN):
            self.advance()
        self.skip_nl()
        then_body = self._parse_block()"""
assert old in content, '_parse_if not found'
content = content.replace(old, new)
changes += 1

# === Fix 13: Handle 'let be NAME' after let mut ===
# The current _parse_let handles let mut, but we need to also handle let be NAME
# When we see 'let be', it should be: let + be + NAME = value
# Currently the parser does: let, then expects ident (be is accepted as ident), then looks for : or be or =
# But 'be' would be consumed as the name. We need to detect 'let be' as a special case.
old = """    def _parse_let(self):
        self.expect(TT.LET)
        # Handle: let mut NAME (or let be NAME) - optional mut/be after let
        is_mut = False
        if self.at(TT.MUT):
            is_mut = True
            self.advance()
        # Handle: let self.x = value (property assignment)
        if self.at(TT.SELF):"""
new = """    def _parse_let(self):
        self.expect(TT.LET)
        # Handle: let mut NAME or let be NAME - optional keywords after let
        is_mut = False
        if self.at(TT.MUT):
            is_mut = True
            self.advance()
        elif self.at(TT.BE) and self.pos + 1 < len(self.tokens) and self.tokens[self.pos + 1].tt in (TT.IDENT,) + tuple([TT.IDENT]):
            # 'let be NAME = value' - be is a binding keyword here
            # But we need to make sure it's not 'let be value' (which would be let name=be be value)
            # Heuristic: if the token after 'be' is an identifier, treat be as a keyword
            self.advance()
        # Handle: let self.x = value (property assignment)
        if self.at(TT.SELF):"""
assert old in content, '_parse_let start not found'
content = content.replace(old, new)
changes += 1

# === Fix 14: Handle 'let _ be X = Y' - use assign_or_expr for value ===
# Already fixed in batch 1, but let me verify

# === Fix 15: Handle _parse_for destructuring ===
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
        if self.at(TT.LPAREN):
            # Destructuring: for (a, b, c) in iterable do ... end
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
                iterable = self._parse_expr()
                self.skip_nl()
                if self.at(TT.DO):
                    self.advance()
                    self.skip_nl()
                body = self._parse_block()
                self.expect(TT.END)
                self.skip_nl()
                return Node('for_in', data={'var': 'tuple', 'iterable': iterable, 'destructure': names}, children=body)
        name = self.advance().val
        if self.at(TT.IN):"""
assert old in content, '_parse_for start not found'
content = content.replace(old, new)
changes += 1

# === Fix 16: Handle multi-line for-in/for-c ===
old = """            # for X in Y [do] ... end
            self.advance()
            iterable = self._parse_expr()
            self.skip_nl()"""
new = """            # for X in Y [do] ... end
            self.advance()
            self.skip_nl()
            iterable = self._parse_expr()
            self.skip_nl()"""
assert old in content, 'for-in iterable not found'
content = content.replace(old, new)
changes += 1

old = """            limit = self._parse_expr()
            self.skip_nl()
            if self.at(TT.DO):"""
new = """            self.skip_nl()
            limit = self._parse_expr()
            self.skip_nl()
            if self.at(TT.DO):"""
assert old in content, 'for-c limit not found'
content = content.replace(old, new)
changes += 1

# === Fix 17: Handle multi-line while ===
old = """    def _parse_while(self):
        self.expect(TT.WHILE)
        condition = self._parse_expr()
        self.skip_nl()
        if self.at(TT.DO):"""
new = """    def _parse_while(self):
        self.expect(TT.WHILE)
        self.skip_nl()
        condition = self._parse_expr()
        self.skip_nl()
        if self.at(TT.DO):"""
assert old in content, '_parse_while not found'
content = content.replace(old, new)
changes += 1

# === Fix 18: Handle multi-line match ===
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
assert old in content, '_parse_match not found'
content = content.replace(old, new)
changes += 1

# === Fix 19: Handle multi-line entity construction ===
# Add skip_nl in entity field parsing
old = """                if not self.at(TT.RBRACE):
                    # Check if this is a list constructor {expr, expr, ...} or entity construct {name=val, ...}"""
# This is already handled by the generic type changes above

# === Fix 20: Handle skip_nl in _parse_assign_or_expr ===
old = """    def _parse_assign_or_expr(self):
        expr = self._parse_expr()
        if self.at(TT.EQ):"""
new = """    def _parse_assign_or_expr(self):
        expr = self._parse_expr()
        self.skip_nl()
        if self.at(TT.EQ):"""
assert old in content, '_parse_assign_or_expr not found'
content = content.replace(old, new)
changes += 1

# === Fix 21: Handle skip_nl in const value parsing ===
old = """        self.expect(TT.EQ)
        value = self._parse_expr()
        self.skip_nl()
        return Node('const', data={'name': name, 'type': type_ann, 'value': value})"""
new = """        self.expect(TT.EQ)
        self.skip_nl()
        value = self._parse_expr()
        self.skip_nl()
        return Node('const', data={'name': name, 'type': type_ann, 'value': value})"""
assert old in content, '_parse_const value not found'
content = content.replace(old, new)
changes += 1

# === Fix 22: Handle skip_nl in property default parsing ===
old = """                if self.at(TT.EQ):
                    self.advance()
                    default = self._parse_expr()
                properties.append({"""
new = """                if self.at(TT.EQ):
                    self.advance()
                    self.skip_nl()
                    default = self._parse_expr()
                    self.skip_nl()
                properties.append({"""
assert old in content, 'Property default not found'
content = content.replace(old, new)
changes += 1

# === Fix 23: Handle skip_nl in _parse_export ===
old = """        # export {A, B, C}
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
                    self.skip_nl()"""
new = """        # export {A, B, C}
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
                    self.skip_nl()"""
# This is already correct
# changes += 1

# === Fix 24: Handle skip_nl in _parse_assign_or_expr after let self.x ===
old = """                if self.at(TT.BE) or self.at(TT.EQ):
                    self.advance()
                    value = self._parse_assign_or_expr()
                else:
                    value = None"""
new = """                if self.at(TT.BE) or self.at(TT.EQ):
                    self.advance()
                    self.skip_nl()
                    value = self._parse_assign_or_expr()
                else:
                    value = None"""
assert old in content, 'self.x let value not found'
content = content.replace(old, new)
changes += 1

# === Fix 25: Handle skip_nl in _parse_block for entity properties ===
# The _parse_block already handles NEWLINE, but add COMMA handling too
# Actually, let's also add 'do' as a valid block terminator

# === Fix 26: Handle match arm with 'then' keyword ===
old = """            if self.at(TT.DO):
                self.advance()
                self.skip_nl()
                body = self._parse_match_arm_body(True)
            elif self.at(TT.RETURN):
                body = [self._parse_return()]
                self.skip_nl()
            else:
                body = self._parse_match_arm_body(False)
            arms.append((pattern, body))
        return arms"""
new = """            if self.at(TT.DO):
                self.advance()
                self.skip_nl()
                body = self._parse_match_arm_body(True)
            elif self.at(TT.THEN):
                self.advance()
                self.skip_nl()
                body = self._parse_match_arm_body(False)
            elif self.at(TT.RETURN):
                body = [self._parse_return()]
                self.skip_nl()
            else:
                body = self._parse_match_arm_body(False)
            arms.append((pattern, body))
        return arms"""
assert old in content, 'match arms DO handling not found'
content = content.replace(old, new)
changes += 1

# === Fix 27: Handle skip_nl in _parse_match_as_expr ===
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
assert old in content, '_parse_match_as_expr not found'
content = content.replace(old, new)
changes += 1

# === Fix 28: Handle 'then' as separator in match arm (already have DO) ===
# Also handle pattern => expr  where expr might be on the same line

# === Fix 29: Handle 'do...end' in if expression context ===
# The _parse_if already handles this through _parse_block

# === Fix 30: Handle assignment in match arm body ===
# In _parse_match_arm_body, the _parse_statement call handles assignments
# through _parse_assign_or_expr which we already fixed

print(f'Total changes applied: {changes}')

with open('bootstrap/orren_bootstrap.py', 'w', encoding='utf-8') as f:
    f.write(content)

print(f'File written. Total lines: {len(content.split(chr(10)))}')
