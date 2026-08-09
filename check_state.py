#!/usr/bin/env python3
with open('bootstrap/orren_bootstrap.py', 'r', encoding='utf-8') as f:
    content = f.read()

checks = [
    ('_push_token method', 'def _push_token' in content),
    ('generic type in primary', 'Check for generic type' in content),
    ('lambda support', "Node('lambda'" in content),
    ('tuple return', "Node('tuple'" in content),
    ('tuple in primary', 'Parenthesized expression or tuple' in content),
    ('for destructuring', 'destructure' in content),
    ('let be NAME handling', 'at(TT.BE) and self.pos + 1' in content),
    ('match THEN handling', 'elif self.at(TT.THEN):' in content),
    ('SHIFT_LEFT in tokenizer', "source[i:i + 2] == '<<'" in content),
    ('SHIFT_RIGHT in tokenizer', 'SHIFT_RIGHT' in content and 'tokens.append(Token(TT.SHIFT_RIGHT' in content),
    ('_parse_type with SHIFT_RIGHT', 'if self.at(TT.SHIFT_RIGHT):' in content),
    ('shift/bitwise levels', '_parse_shift' in content and '_parse_bitwise' in content),
    ('_parse_expr uses _parse_logical_or', '_parse_logical_or' in content),
    ('for-in skip_nl', content.count('iterable = self._parse_expr()') >= 2),
    ('_parse_if skip_nl after IF', 'expect(TT.IF)\n' in content and 'skip_nl()' in content),
    ('mut keyword', "'mut': TT.MUT" in content),
    ('depth tracking', 'depth = 0' in content),
    ('list constructor', 'is_list_constructor' in content),
    ('return tuple', 'return (a, b)' in content or 'Node(\'tuple\'' in content),
    ('assign_or_expr skip_nl', '_parse_assign_or_expr' in content and 'skip_nl' in content),
]

for name, status in checks:
    print(f'  {name}: {"YES" if status else "NO"}')
