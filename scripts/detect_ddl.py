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

# 🔥 Robust changed file detection
print("Getting changed files from latest commit...")

changed_files = git_output([
    "git",
    "show",
    "--pretty=",
    "--name-only",
    "HEAD"
]).splitlines()

print("Changed files:", changed_files)

ddl_files = [f for f in changed_files if f.lower().endswith(".sql")]

# ✅ Case 1: No SQL changes
if not ddl_files:
    print("No DDL changes")

    with open(output_path, "w") as f:
        json.dump({"file": None, "ddl": None, "is_drop": False}, f, indent=2)

    print("##vso[task.setvariable variable=IS_DROP;isOutput=true]false")
    sys.exit(0)

ddl_file = ddl_files[0]

print(f"Reading diff from {ddl_file}")

diff = git_output([
    "git",
    "show",
    "HEAD",
    "--",
    ddl_file
])

ddl_stmt = None

for line in diff.splitlines():

    if line.startswith(("+++", "---")):
        continue

    if not line.startswith(("+", "-")):
        continue

    stmt = line[1:].strip()

    if not stmt:
        continue

    stmt_upper = stmt.upper()

    if (
        stmt_upper.startswith("CREATE")
        or stmt_upper.startswith("DROP")
        or stmt_upper.startswith("ALTER")
    ):
        ddl_stmt = stmt
        break

# ✅ Case 2: No executable DDL
if not ddl_stmt:
    print("No executable DDL found")

    with open(output_path, "w") as f:
        json.dump({"file": None, "ddl": None, "is_drop": False}, f, indent=2)

    print("##vso[task.setvariable variable=IS_DROP;isOutput=true]false")
    sys.exit(0)

# ✅ Case 3: Valid DDL
is_drop = ddl_stmt.upper().startswith("DROP")

with open(output_path, "w") as f:
    json.dump({
        "file": ddl_file,
        "ddl": ddl_stmt,
        "is_drop": is_drop
    }, f, indent=2)

print("DDL detected:", ddl_stmt)
print("IS_DROP:", is_drop)

print(f"##vso[task.setvariable variable=IS_DROP;isOutput=true]{str(is_drop).lower()}")
