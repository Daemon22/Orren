#!/usr/bin/env python3
"""Fix entity construction with list-like constructor support."""

path = 'bootstrap/orren_bootstrap.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Use the EXACT content from the file (line 1306-1333)
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
                        self.skip_nl()
                self.skip_nl()
                self.expect(TT.RBRACE)
                return Node('construct', data={'name': t.val, 'fields': fields})"""

new = """                fields = {}
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
                return Node('construct', data={'name': generic_name, 'fields': fields})"""

if old in content:
    content = content.replace(old, new, 1)
    print('Entity construction change applied!')
    with open('bootstrap/orren_bootstrap.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print(f'File written. Total lines: {len(content.split(chr(10)))}')
else:
    print('ERROR: old string not found')
    # Try to find partial match
    for i in range(len(old), 0, -1):
        if content.find(old[:i]) >= 0:
            print(f'Longest match: {i} chars out of {len(old)}')
            # Find where it fails
            idx = content.find(old[:i])
            file_snippet = content[idx:idx+50]
            if i < len(old):
                next_char_file = content[idx+i] if idx+i < len(content) else 'EOF'
                next_char_target = old[i] if i < len(old) else 'EOF'
                print(f'File char at pos {i}: {repr(next_char_file)}')
                print(f'Target char at pos {i}: {repr(next_char_target)}')
            break
