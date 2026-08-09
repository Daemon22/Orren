import os
import subprocess

passed = []
failed = []

for root, dirs, files in os.walk('.'):
    if 'bootstrap' in root or '.git' in root or '__pycache__' in root:
        continue
    for f in files:
        if f.endswith('.orn'):
            path = os.path.join(root, f)
            result = subprocess.run(
                ['python', 'bootstrap/orren_bootstrap.py', 'check', path],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                passed.append(path)
            else:
                error_line = (result.stderr or result.stdout or '').strip().split(chr(10))[0][:120]
                failed.append((path, error_line))

print(f"=== PASSED: {len(passed)} ===")
for p in passed:
    print(f"  {p}")

print(f"\n=== FAILED: {len(failed)} ===")
for p, err in failed:
    print(f"  {p}: {err}")
