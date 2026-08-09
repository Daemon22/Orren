with open('bootstrap/orren_bootstrap.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Check tokenizer for -> handling
lines = content.split('\n')
for i, line in enumerate(lines):
    if '->' in line and i < 300:  # tokenizer section is early in file
        print(f'L{i+1}: {line.strip()[:80]}')

# Also check FAT_ARROW assignment
for i, line in enumerate(lines):
    if 'FAT_ARROW' in line:
        print(f'L{i+1}: {line.strip()[:80]}')
