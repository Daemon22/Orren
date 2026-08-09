import os
with open('bootstrap/orren_bootstrap.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find SHIFT_RIGHT occurrences
count = content.count('SHIFT_RIGHT')
print(f'SHIFT_RIGHT occurrences: {count}')

# Find the >> handling in tokenizer
idx = content.find('source[i:i + 2] == \'>\'\'')
print(f"Found >> handling at index: {idx}")

# Show all lines with >>
lines = content.split('\n')
for i, line in enumerate(lines):
    if '>>' in line and 'SHIFT_RIGHT' in line:
        print(f'L{i+1}: {line.strip()[:100]}')
    if 'SHIFT_RIGHT' in line:
        print(f'L{i+1}: {line.strip()[:100]}')
