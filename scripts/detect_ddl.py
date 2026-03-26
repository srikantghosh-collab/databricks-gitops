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
        ["git", "show", "--pretty=", "--name-status", "HEAD", "--", DDL_FOLDER],
        text=True
    ).splitlines()
except subprocess.CalledProcessError:
    changed_files = []

scripts = []

for raw_line in changed_files:
    raw_line = raw_line.strip()
    if not raw_line:
        continue

    parts = raw_line.split("\t")
    status = parts[0]
    file_path = None

    # Renames appear like: R076 <old_path> <new_path>
    if status.startswith("R") and len(parts) >= 3:
        file_path = parts[2]
    elif status.startswith("D"):
        # Deleted files should not be executed in the current checkout.
        continue
    elif len(parts) >= 2:
        file_path = parts[1]
    else:
        continue

    if not file_path.startswith(f"{DDL_FOLDER}/") or not file_path.endswith(".sql"):
        continue

    if not os.path.exists(file_path):
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

# Get commit id


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
