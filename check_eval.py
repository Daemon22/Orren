with open('bootstrap/orren_bootstrap.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Check FAT_ARROW handling
if 'FAT_ARROW' in content:
    idx = content.find("'->'")
    if idx == -1:
        idx = content.find('FAT_ARROW')
        print(f"FAT_ARROW found at index {idx}")
        # Check context
        start = max(0, idx - 50)
        end = min(len(content), idx + 100)
        print(f"Context: {repr(content[start:end])}")
else:
    print("FAT_ARROW not found in content")

# Check for -> handling
if "'->'" in content:
    print("-> string found")
elif '"->"' in content:
    print('-> double-quoted string found')

# Check tokenizer for ->
idx = content.find("source[i:i + 2] == '->'")
if idx >= 0:
    print(f"\n-> tokenizer handling found at {idx}")
else:
    # Check for -> in any form
    for line in content.split('\n'):
        if '->' in line and 'FAT' in line:
            print(f"FAT_ARROW line: {line.strip()}")

# Check evaluator for list_literal, lambda, tuple
for node_type in ['list_literal', 'lambda', 'tuple']:
    idx = content.find(f"kind == '{node_type}'")
    if idx >= 0:
        start = max(0, idx - 20)
        end = min(len(content), idx + 100)
        print(f"\n{node_type} handling found:")
        print(content[start:end])
    else:
        print(f"\n{node_type} handling NOT found - needs adding")

# Check what's after _parse_logical_and in _parse_comparison chain
idx = content.find('def _parse_logical_or')
end = content.find('def ', idx + 20)
print(f"\n_parse_logical_or: {content[idx:end]}")

# Check _parse_comparison
idx = content.find('def _parse_comparison')
end = content.find('def ', idx + 20)
print(f"\n_parse_comparison: {content[idx:end]}")

# Check _parse_additive
idx = content.find('def _parse_additive')
end = content.find('def ', idx + 20)
print(f"\n_parse_additive: {content[idx:end]}")
