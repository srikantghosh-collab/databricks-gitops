import subprocess
import json
import sys
import os
import re

print("Detecting DDL changes...")

DDL_FILE = "ddl/orders.sql"

output_path = os.path.join(
    os.environ.get("SYSTEM_DEFAULTWORKINGDIRECTORY", "."),
    "ddl_output.json"
)

# If SQL file does not exist
if not os.path.exists(DDL_FILE):
    print("No SQL file found")

    with open(output_path, "w") as f:
        json.dump({"ddls": [], "is_drop": False}, f, indent=2)

    print("##vso[task.setvariable variable=IS_DROP;isOutput=true]false")
    sys.exit(0)


# Read full SQL file
with open(DDL_FILE, "r") as f:
    sql_text = f.read()


# Split SQL statements safely
def split_sql_statements(sql):
    statements = []
    buffer = ""

    for line in sql.splitlines():
        line = line.strip()

        if not line or line.startswith("--"):
            continue

        buffer += " " + line

        if ";" in line:
            statements.append(buffer.strip())
            buffer = ""

    if buffer:
        statements.append(buffer.strip())

    return statements


statements = split_sql_statements(sql_text)

ddl_list = []

for stmt in statements:
    stmt_upper = stmt.upper()

    if stmt_upper.startswith(("CREATE", "ALTER", "DROP")):
        ddl_list.append({
            "statement": stmt,
            "type": stmt_upper.split()[0]
        })


# No DDL found
if not ddl_list:
    print("No executable DDL found")

    with open(output_path, "w") as f:
        json.dump({"ddls": [], "is_drop": False}, f, indent=2)

    print("##vso[task.setvariable variable=IS_DROP;isOutput=true]false")
    sys.exit(0)


# Check if any DROP exists
is_drop = any(d["type"] == "DROP" for d in ddl_list)


# Write artifact
with open(output_path, "w") as f:
    json.dump(
        {
            "commit_id": subprocess.check_output(
                ["git", "rev-parse", "HEAD"],
                text=True
            ).strip(),
            "ddls": ddl_list,
            "is_drop": is_drop
        },
        f,
        indent=2,
    )

print(f"{len(ddl_list)} DDL statements detected")
print("IS_DROP:", is_drop)

print(f"##vso[task.setvariable variable=IS_DROP;isOutput=true]{str(is_drop).lower()}")
