import subprocess
import sys
import json

# 1. Get changed files
changed_files = subprocess.check_output(
    ["git", "diff", "--name-only", "HEAD~1", "HEAD"],
    text=True
).splitlines()

# 2. Filter only ddl folder
ddl_files = [f for f in changed_files if f.startswith("ddl/")]

if not ddl_files:
    print("No DDL changes detected")
    sys.exit(0)

ddl_file = ddl_files[0]

# 3. Get actual diff of ddl file
ddl_diff = subprocess.check_output(
    ["git", "diff", "HEAD~1", "HEAD", "--", ddl_file],
    text=True
)

# 4. Extract executable DDL
ddl_line = None
for line in ddl_diff.splitlines():
    if line.startswith("+") and not line.startswith("+++"):
        ddl_line = line.replace("+", "").strip()
        break

if not ddl_line:
    print("DDL file changed but no executable statement found")
    sys.exit(0)

# 5. Save output
with open("ddl_output.json", "w") as f:
    json.dump(
        {
            "file": ddl_file,
            "ddl": ddl_line
        },
        f,
        indent=2
    )

print("Detected DDL:", ddl_line)
