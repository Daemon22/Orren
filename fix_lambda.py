#!/usr/bin/env python3
"""Fix lambda to use TT.ARROW instead of TT.FAT_ARROW, and add evaluator support."""

path = 'bootstrap/orren_bootstrap.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

applied = 0

# === Fix 1: Change lambda to use TT.ARROW instead of TT.FAT_ARROW ===
old = """            self.skip_nl()
            self.expect(TT.FAT_ARROW)
            body_expr = self._parse_expr()
            self.skip_nl()
            return Node('lambda', data={'params': params, 'body': body_expr})"""
new = """            self.skip_nl()
            self.expect(TT.ARROW)
            body_expr = self._parse_expr()
            self.skip_nl()
            return Node('lambda', data={'params': params, 'body': body_expr})"""
if old in content:
    content = content.replace(old, new, 1)
    applied += 1
    print('Fix 1: Lambda uses TT.ARROW')
else:
    print('Fix 1: SKIP - lambda not found')

# === Fix 2: Add lambda evaluation support ===
# Find the list_literal handling in the evaluator
old = """        if kind == 'list_literal':
            return [self._eval_expr(e, env) for e in node.data['elements']]"""
new = """        if kind == 'list_literal':
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
            return tuple(self._eval_expr(e, env) for e in node.data['elements'])"""
if old in content:
    content = content.replace(old, new, 1)
    applied += 1
    print('Fix 2: Lambda + tuple evaluator support')
else:
    print('Fix 2: SKIP - list_literal handler not found')

# === Fix 3: Handle lambda calls in evaluator ===
# When a lambda value is called, invoke it
old = """        if kind == 'call':
            callee = self._eval_expr(node.data['callee'], env)"""
new = """        if kind == 'call':
            callee = self._eval_expr(node.data['callee'], env)
            # Handle lambda calls
            if hasattr(callee, '__call__') and not isinstance(callee, OrrenEntity) and not isinstance(callee, type(None)):
                args = [self._eval_expr(a, env) for a in node.data['args']]
                return callee(args, env)"""
if old in content:
    content = content.replace(old, new, 1)
    applied += 1
    print('Fix 3: Lambda call handling')
else:
    print('Fix 3: SKIP - call handler not found')

# === Fix 4: Handle tuple values in comparisons/operations ===
# When comparing tuples, convert to tuple if not already
old = """        if kind == 'binop':
            op = node.data['op']
            left = self._eval_expr(node.data['left'], env)
            right = self._eval_expr(node.data['right'], env)"""
new = """        if kind == 'binop':
            op = node.data['op']
            left = self._eval_expr(node.data['left'], env)
            right = self._eval_expr(node.data['right'], env)
            # Handle shift and bitwise operations
            if op == '>>':
                return left >> right
            if op == '<<':
                return left << right
            if op == '&':
                return left & right
            if op == '^':
                return left ^ right"""
if old in content:
    content = content.replace(old, new, 1)
    applied += 1
    print('Fix 4: Shift/bitwise ops in evaluator')
else:
    print('Fix 4: SKIP - binop handler not found')

# === Fix 5: Handle 'is_mut' in let evaluation (ignore it for runtime) ===
# The let node now has 'is_mut' field, but the evaluator should still work
# since it just ignores extra fields

with open('bootstrap/orren_bootstrap.py', 'w', encoding='utf-8') as f:
    f.write(content)

print(f'\nTotal fixes applied: {applied}')
print(f'File written. Total lines: {len(content.split(chr(10)))}')
