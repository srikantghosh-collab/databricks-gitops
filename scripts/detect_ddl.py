import subprocess
import json
import sys
import os

def git_output(cmd):
    return subprocess.check_output(cmd, text=True).strip()

print("Detecting DDL changes...")

output_path = os.path.join(
    os.environ.get("SYSTEM_DEFAULTWORKINGDIRECTORY", "."),
    "ddl_output.json"
)

# Get changed files
try:
    changed_files = git_output(
        ["git", "diff", "--name-only", "HEAD~1", "HEAD"]
    ).splitlines()
except subprocess.CalledProcessError:
    changed_files = git_output(
        ["git", "show", "--name-only", "--pretty=", "HEAD"]
    ).splitlines()

ddl_files = [f for f in changed_files if f.lower().endswith(".sql")]

#  No DDL files
if not ddl_files:
    print("No DDL changes")

    with open(output_path, "w") as f:
        json.dump({"file": None, "ddl": None, "is_drop": False}, f, indent=2)

    print("##vso[task.setvariable variable=IS_DROP;isOutput=true]false")
    sys.exit(0)

ddl_file = ddl_files[0]

# Get diff
try:
    diff = git_output(["git", "diff", "HEAD~1", "HEAD", "--", ddl_file])
except subprocess.CalledProcessError:
    diff = git_output(["git", "show", "HEAD", "--", ddl_file])

ddl_stmt = None

for line in diff.splitlines():

    if line.startswith(("+++", "---")):
        continue

    if not line.startswith("+"):
        continue

    stmt = line[1:].strip()
    stmt_upper = stmt.upper()

    if stmt_upper.startswith(("CREATE", "DROP", "ALTER")):
        ddl_stmt = stmt
        break

#  No executable DDL
if not ddl_stmt:
    print("No executable DDL found")

    with open(output_path, "w") as f:
        json.dump({"file": None, "ddl": None, "is_drop": False}, f, indent=2)

    print("##vso[task.setvariable variable=IS_DROP;isOutput=true]false")
    sys.exit(0)

#  Valid DDL
is_drop = ddl_stmt.upper().startswith("DROP")

with open(output_path, "w") as f:
    json.dump(
        {
            "file": ddl_file,
            "ddl": ddl_stmt,
            "is_drop": is_drop,
        },
        f,
        indent=2,
    )

print("DDL detected:", ddl_stmt)
print("IS_DROP:", is_drop)

print(f"##vso[task.setvariable variable=IS_DROP;isOutput=true]{str(is_drop).lower()}")
