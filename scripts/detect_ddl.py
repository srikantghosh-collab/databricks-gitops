import subprocess
import json
import sys
import os

def git_output(cmd):
    return subprocess.check_output(cmd, text=True)

print("Detecting DDL changes...")

changed_files = git_output(
    ["git", "show", "--name-only", "--pretty=", "HEAD"]
).splitlines()

ddl_files = [f for f in changed_files if f.startswith("ddl/")]

if not ddl_files:
    print("No DDL changes")
    print("##vso[task.setvariable variable=IS_DROP;isOutput=true]false")
    sys.exit(0)

ddl_file = ddl_files[0]
diff = git_output(["git", "show", "HEAD", "--", ddl_file])

ddl_stmt = None
for line in diff.splitlines():
    if line.startswith("+") and not line.startswith("+++"):
        ddl_stmt = line.replace("+", "").strip()
        break

if not ddl_stmt:
    print("No executable DDL found")
    print("##vso[task.setvariable variable=IS_DROP;isOutput=true]false")
    sys.exit(0)

is_drop = ddl_stmt.upper().startswith("DROP")

# 🔥 THIS IS THE KEY LINE
print(f"##vso[task.setvariable variable=IS_DROP;isOutput=true]{str(is_drop).lower()}")

print("DDL:", ddl_stmt)
print("IS_DROP:", is_drop)
























































