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
                line = lines[i]
                next_line = lines[i+1] if i+1 < len(lines) else ''
                stripped = line.strip()
                if stripped.startswith('--') and not stripped.startswith('---'):
                    # Check next non-empty line
                    if next_line.strip() and not next_line.strip().startswith('--') and not next_line.strip().startswith('#') and not next_line.strip().startswith('///'):
                        issues.append((path, i+1, i+2, next_line.strip()))

for path, l1, l2, content in issues:
    print(f'{path}:{l1} -> next line {l2}: "{content[:80]}"')
