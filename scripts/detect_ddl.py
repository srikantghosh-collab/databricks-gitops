import json
import sys
import os
import subprocess

print("Detecting DDL migrations")

DDL_FOLDER = "ddl"
OUTPUT_PATH = "ddl_output.json"

# --------------------------------------------------
# Detect migration SQL files changed in current commit
# --------------------------------------------------

if not os.path.exists(DDL_FOLDER):
    print("DDL folder not found")
    json.dump({"migrations": []}, open(OUTPUT_PATH, "w"))
    sys.exit(0)

try:
    changed_files = subprocess.check_output(
        ["git", "show", "--pretty=", "--name-only", "HEAD", "--", DDL_FOLDER],
        text=True
    ).splitlines()
except subprocess.CalledProcessError:
    changed_files = []

scripts = []

for file_path in changed_files:
    file_path = file_path.strip()

    if not file_path.startswith(f"{DDL_FOLDER}/") or not file_path.endswith(".sql"):
        continue

    # Ignore deleted or renamed-away files so downstream execution only
    # receives migrations that exist in the current workspace checkout.
    if not os.path.exists(file_path):
        print(f"Skipping missing changed file: {file_path}")
        continue

    scripts.append(os.path.basename(file_path))

scripts = sorted(set(scripts))

if not scripts:
    print("No changed SQL migration files found in current commit")
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
