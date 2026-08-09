import os

issues = []
for root, dirs, files in os.walk('.'):
    if 'bootstrap' in root or '.git' in root:
        continue
    for f in files:
        if f.endswith('.orn'):
            path = os.path.join(root, f)
            lines = open(path, encoding='utf-8').read().split(chr(10))
            for i in range(len(lines)-1):
                line = lines[i].strip()
                next_line = lines[i+1] if i+1 < len(lines) else ''
                next_stripped = next_line.strip()
                # If current line is a comment and next line is non-empty, not a comment, 
                # and starts with spaces (continuation)
                if line.startswith('--') and not line.startswith('---'):
                    if next_stripped and not next_stripped.startswith('--') and \
                       not next_stripped.startswith('#') and not next_stripped.startswith('///') and \
                       not next_stripped.startswith('intent') and \
                       next_line.startswith('  ') and \
                       not next_stripped.startswith(('entity', 'enum', 'fn', 'let', 'const', 'if', 'for', 
                       'while', 'match', 'with', 'return', 'else', 'then', 'do', 'end', 'case',
                       'import', 'module', 'export', 'property', 'self', 'true', 'false')):
                        issues.append((path, i+1, i+2, next_stripped[:80]))

for path, l1, l2, content in issues:
    print(f'{path}:{l1} -> next line {l2}: "{content}"')
