import subprocess
import json
import sys

def git_output(cmd):
    return subprocess.check_output(cmd, text=True).strip()

print("Detecting DDL changes...")

changed_files = git_output(
    ["git", "show", "--name-only", "--pretty=", "HEAD"]
).splitlines()

ddl_files = [f for f in changed_files if f.startswith("ddl/")]

if not ddl_files:
    print("##vso[task.setvariable variable=ddl_found]false")
    sys.exit(0)

ddl_file = ddl_files[0]

diff = git_output(["git", "show", "HEAD", "--", ddl_file])

ddl_stmt = None
for line in diff.splitlines():
    if line.startswith("+") and not line.startswith("+++"):
        ddl_stmt = line.replace("+", "").strip()
        break

if not ddl_stmt:
    print("##vso[task.setvariable variable=ddl_found]false")
    sys.exit(0)

is_drop = ddl_stmt.upper().startswith("DROP")

# 🔥 SET PIPELINE VARIABLES
print(f"##vso[task.setvariable variable=ddl_found]true")
print(f"##vso[task.setvariable variable=is_drop]{str(is_drop).lower()}")

print("DDL:", ddl_stmt)
print("IS_DROP:", is_drop)

with open("ddl_output.json", "w") as f:
    json.dump(
        {"file": ddl_file, "ddl": ddl_stmt, "is_drop": is_drop},
        f,
        indent=2
    )




















































