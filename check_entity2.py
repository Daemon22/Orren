with open('bootstrap/orren_bootstrap.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the fields = {} block near construct
idx = content.find("fields = {}")
# Find the one after _parse_primary's IDENT section
idx = content.find("fields = {}", content.find("generic_name = t.val"))
end = content.find("return Node('ident'", idx)
if end == -1:
    end = content.find("# For Name(args)", idx)
print(content[idx:end])
print('---END---')
