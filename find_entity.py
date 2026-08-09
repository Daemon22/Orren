with open('bootstrap/orren_bootstrap.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find the fields = {} line near construct
for i, line in enumerate(lines):
    if 'fields = {}' in line:
        # Check context - is this in _parse_primary?
        context_start = max(0, i-10)
        if 'generic_name' in ''.join(lines[context_start:i]):
            print(f'Found at line {i+1}')
            # Print from this line to the construct return
            for j in range(i, min(len(lines), i+40)):
                print(f'{j+1}: {repr(lines[j])}')
            break
