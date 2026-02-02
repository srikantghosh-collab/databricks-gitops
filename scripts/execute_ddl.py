import subprocess
import sys
import json

def git_output(cmd):
    return subprocess.check_output(cmd, text=True).strip()

print("Detecting DDL changes from latest commit...")

# Get files changed in current commit
changed_files = git_output(
    ["git", "show", "--name-only", "--pretty=", "HEAD"]
).splitlines()

ddl_files = [f for f in changed_files if f.startswith("ddl/")]

if not ddl_files:
    print("No DDL changes detected.")
    sys.exit(0)

ddl_file = ddl_files[0]

# Get diff of that file in current commit
diff = git_output(
    ["git", "show", "HEAD", "--", ddl_file]
)

ddl = None
for line in diff.splitlines():
    if line.startswith("+") and not line.startswith("+++"):
        ddl = line.replace("+", "").strip()
        break

if not ddl:
    print("DDL file changed but no executable DDL found.")
    sys.exit(0)

with open("ddl_output.json", "w") as f:
    json.dump(
        {"file": ddl_file, "ddl": ddl},
        f,
        indent=2
    )

print("Detected DDL:", ddl)
