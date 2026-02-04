import subprocess
import sys

def git_output(cmd):
    return subprocess.check_output(cmd, text=True).strip()

print("Detecting DDL changes...")

changed_files = git_output(
    ["git", "show", "--name-only", "--pretty=", "HEAD"]
).splitlines()

ddl_files = [f for f in changed_files if f.startswith("ddl/")]

if not ddl_files:
    print("##vso[task.setvariable variable=IS_DDL;isOutput=true]false")
    print("No DDL changes detected")
    sys.exit(0)

ddl_file = ddl_files[0]

diff = git_output(["git", "show", "HEAD", "--", ddl_file])

ddl_stmt = None
for line in diff.splitlines():
    if line.startswith("+") and not line.startswith("+++"):
        ddl_stmt = line.replace("+", "").strip()
        break

if not ddl_stmt:
    print("##vso[task.setvariable variable=IS_DDL;isOutput=true]false")
    print("No executable DDL found")
    sys.exit(0)

is_drop = ddl_stmt.upper().startswith("DROP")

print(f"Detected DDL: {ddl_stmt}")
print(f"IS_DROP: {is_drop}")

print(f"##vso[task.setvariable variable=IS_DROP;isOutput=true]{str(is_drop).lower()}")


