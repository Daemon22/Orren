with open('bootstrap/orren_bootstrap.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Print lines 1306-1333
for i in range(1305, 1333):
    print(f'{i+1}: {repr(lines[i])}')
