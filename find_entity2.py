with open('bootstrap/orren_bootstrap.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Check exact whitespace of line 1306
print(f"Line 1306 repr: {repr(lines[1305])}")
print(f"Line 1307 repr: {repr(lines[1306])}")

# Check if the issue is tabs vs spaces
print(f"Line 1306 starts with tab: {'\\t' in lines[1305][:5]}")
print(f"Line 1306 leading spaces: {len(lines[1305]) - len(lines[1305].lstrip())}")

# Build the exact old string from the file
old_lines = []
for i in range(1305, 1333):  # lines 1306 to 1333
    old_lines.append(lines[i])
old_str = ''.join(old_lines)
print(f"\nOld string (last 50 chars): {repr(old_str[-50:])}")
print(f"Old string length: {len(old_str)}")

# Check if our target old string matches
target = """                fields = {}
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

print(f"\nTarget length: {len(target)}")
print(f"Match: {old_str == target}")

# Find difference
if old_str != target:
    for i, (a, b) in enumerate(zip(old_str, target)):
        if a != b:
            print(f"First diff at char {i}: file has {repr(a)}, target has {repr(b)}")
            print(f"  Context file: ...{repr(old_str[max(0,i-10):i+10])}...")
            print(f"  Context target: ...{repr(target[max(0,i-10):i+10])}...")
            break
