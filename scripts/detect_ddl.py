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

try:
    changed_files = git_output(
        ["git", "diff", "--name-only", "HEAD~1", "HEAD"]
    ).splitlines()
except subprocess.CalledProcessError:
    print("Fallback: using git show HEAD")
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

try:
    diff = git_output(
        ["git", "diff", "HEAD~1", "HEAD", "--", ddl_file]
    )
except subprocess.CalledProcessError:
    diff = git_output(
        ["git", "show", "HEAD", "--", ddl_file]
    )


ddls = []

ddl_candidates = []

for line in diff.splitlines():

    # Ignore git headers
    if line.startswith(("+++", "---")):
        continue

    # Only + or - lines
    if not line.startswith(("+", "-")):
        continue

    stmt = line[1:].strip()

    # Skip empty lines
    if not stmt:
        continue

    stmt_upper = stmt.upper()

    if (
        "CREATE TABLE" in stmt_upper
        or "DROP TABLE" in stmt_upper
        or "ALTER TABLE" in stmt_upper
    ):
        ddl_candidates.append(stmt)

# Pick latest DDL change
ddl_stmt = ddl_candidates[-1] if ddl_candidates else None



# ✅ Case 2: No executable DDL
if not ddls:
    print("No executable DDL found")

    with open(output_path, "w") as f:
        json.dump({"file": None, "ddls": []}, f, indent=2)

    print("##vso[task.setvariable variable=IS_DROP;isOutput=true]false")
    sys.exit(0)

# ✅ Case 3: Valid DDL found
is_drop = any(d["type"] == "DROP" for d in ddls)

with open(output_path, "w") as f:
    json.dump({
        "file": ddl_file,
        "ddls": ddls
    }, f, indent=2)

print("Detected DDLs:")
for d in ddls:
    print("-", d["stmt"])

print("IS_DROP:", is_drop)


print(f"##vso[task.setvariable variable=IS_DROP;isOutput=true]{str(is_drop).lower()}")

























































