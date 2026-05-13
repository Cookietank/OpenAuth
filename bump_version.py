import sys
import re

if len(sys.argv) < 2:
    print("Error: No version provided.")
    sys.exit(1)

new_version = sys.argv[1]

# Read app.py
with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find and replace the APP_VERSION variable
new_content = re.sub(r'APP_VERSION\s*=\s*".*?"', f'APP_VERSION = "v{new_version}"', content)

# Write it back
with open('app.py', 'w', encoding='utf-8') as f:
    f.write(new_content)

print(f"✅ app.py successfully updated to v{new_version}")