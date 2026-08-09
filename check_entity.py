import sys
with open('bootstrap/orren_bootstrap.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the construct return in _parse_primary
idx = content.find("return Node('construct'")
end = content.find("return Node('ident'", idx)
if end == -1:
    end = idx + 2000
print(content[idx:end])
print('---END---')
