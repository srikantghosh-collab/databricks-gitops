import subprocess
import json
import sys
import os

def git_output(cmd):
    return subprocess.check_output(cmd, text=True).strip()

print("Detecting DDL changes...")

# Force output file in repo root
output_path = os.path.join(
    os.environ.get("SYSTEM_DEFAULTWORKINGDIRECTORY", "."),
    "ddl_output.json"
)

changed_files = git_output(
    ["git", "show", "--name-only", "--pretty=", "HEAD"]
).splitlines()

ddl_files = [
    f for f in changed_files
    if f.lower().endswith(".sql")
]

# ✅ Case 1: No DDL changes
if not ddl_files:
    print("No DDL changes")

    with open(output_path, "w") as f:
        json.dump(
            {
                "file": None,
                "ddl": None,
                "is_drop": False
            },
            f,
            indent=2
        )

    print("Empty artifact created")
    print("##vso[task.setvariable variable=IS_DROP;isOutput=true]false")
    sys.exit(0)

ddl_file = ddl_files[0]

diff = git_output(["git", "show", "HEAD", "--", ddl_file])

ddl_stmt = None
for line in diff.splitlines():
    if line.startswith("+") and not line.startswith("+++"):
        ddl_stmt = line.replace("+", "").strip()
        break

# ✅ Case 2: No executable DDL
if not ddl_stmt:
    print("No executable DDL found")

    with open(output_path, "w") as f:
        json.dump(
            {
                "file": None,
                "ddl": None,
                "is_drop": False
            },
            f,
            indent=2
        )

    print("Empty artifact created")
    print("##vso[task.setvariable variable=IS_DROP;isOutput=true]false")
    sys.exit(0)

# ✅ Case 3: Valid DDL found
is_drop = ddl_stmt.upper().startswith("DROP")

with open(output_path, "w") as f:
    json.dump(
        {
            "file": ddl_file,
            "ddl": ddl_stmt,
            "is_drop": is_drop
        },
        f,
        indent=2
    )

print("DDL artifact created")
print("DDL:", ddl_stmt)
print("IS_DROP:", is_drop)

print(f"##vso[task.setvariable variable=IS_DROP;isOutput=true]{str(is_drop).lower()}")

























































