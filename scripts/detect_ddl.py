import json
import sys
import os
import subprocess

print("Detecting DDL migrations")

DDL_FOLDER = "ddl"
OUTPUT_PATH = "ddl_output.json"

# --------------------------------------------------
# Detect migration SQL files
# --------------------------------------------------

if not os.path.exists(DDL_FOLDER):
    print("DDL folder not found")
    json.dump({"migrations": []}, open(OUTPUT_PATH, "w"))
    sys.exit(0)

scripts = sorted([
    f for f in os.listdir(DDL_FOLDER)
    if f.endswith(".sql")
])

if not scripts:
    print("No SQL migration files found")
    json.dump({"migrations": []}, open(OUTPUT_PATH, "w"))
    sys.exit(0)

migrations = []

for script in scripts:
    migrations.append({
        "script_name": script,
        "path": f"{DDL_FOLDER}/{script}"
    })

# --------------------------------------------------
# Get commit id
# --------------------------------------------------

commit_id = subprocess.check_output(
    ["git", "rev-parse", "HEAD"],
    text=True
).strip()

# --------------------------------------------------
# Write artifact
# --------------------------------------------------

json.dump(
    {
        "commit_id": commit_id,
        "migrations": migrations
    },
    open(OUTPUT_PATH, "w"),
    indent=2
)

print(f"{len(migrations)} migration script(s) detected")
print("##vso[task.setvariable variable=IS_DROP;isOutput=true]false")