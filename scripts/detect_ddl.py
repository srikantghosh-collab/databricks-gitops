import json
import sys
import os
import subprocess
import re

print("Detecting DDL changes")

DDL_FILE = "ddl/orders.sql"
OUTPUT_PATH = "ddl_output.json"


def split_sql_statements(sql_text):
    statements = []
    buffer = ""

    for line in sql_text.splitlines():
        line = line.strip()

        if not line or line.startswith("--"):
            continue

        buffer += " " + line

        if ";" in line:
            parts = buffer.split(";")
            for part in parts[:-1]:
                stmt = part.strip()
                if stmt:
                    statements.append(stmt)
            buffer = parts[-1]

    return statements


def extract_table_name(stmt):
    patterns = [
        r"CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+([^\s(]+)",
        r"CREATE\s+TABLE\s+([^\s(]+)",
        r"ALTER\s+TABLE\s+([^\s;]+)",
        r"DROP\s+TABLE\s+IF\s+EXISTS\s+([^\s;]+)",
        r"DROP\s+TABLE\s+([^\s;]+)",
        r"INSERT\s+INTO\s+([^\s(]+)"
    ]

    for pattern in patterns:
        match = re.search(pattern, stmt, re.IGNORECASE)
        if match:
            return match.group(1)

    return None


# --------------------------------------------------
# Validate SQL file exists
# --------------------------------------------------

if not os.path.exists(DDL_FILE):
    print("No DDL SQL file found")
    json.dump({"ddls": [], "is_drop": False}, open(OUTPUT_PATH, "w"))
    print("##vso[task.setvariable variable=IS_DROP;isOutput=true]false")
    sys.exit(0)


# --------------------------------------------------
# Read SQL file
# --------------------------------------------------

with open(DDL_FILE) as f:
    sql_text = f.read()

statements = split_sql_statements(sql_text)

SQL_PREFIXES = ("CREATE", "ALTER", "DROP", "INSERT", "UPDATE", "DELETE", "MERGE")

ddls = []
counter = 1

for stmt in statements:
    stmt_clean = stmt.strip()
    stmt_upper = stmt_clean.upper()

    if stmt_upper.startswith(SQL_PREFIXES):

        ddl_type = stmt_upper.split()[0]
        table_name = extract_table_name(stmt_clean)

        ddls.append({
            "id": f"ddl_{counter}",
            "statement": stmt_clean,
            "type": ddl_type,
            "table": table_name
        })

        counter += 1


# --------------------------------------------------
# No DDL case
# --------------------------------------------------

if not ddls:
    print("No executable DDL found")
    json.dump({"ddls": [], "is_drop": False}, open(OUTPUT_PATH, "w"))
    print("##vso[task.setvariable variable=IS_DROP;isOutput=true]false")
    sys.exit(0)


# --------------------------------------------------
# Drop detection
# --------------------------------------------------

is_drop = any(d["type"] == "DROP" for d in ddls)


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
        "file": DDL_FILE,
        "ddls": ddls,
        "is_drop": is_drop
    },
    open(OUTPUT_PATH, "w"),
    indent=2
)


print(f"{len(ddls)} DDL statement(s) detected")
print(f"##vso[task.setvariable variable=IS_DROP;isOutput=true]{str(is_drop).lower()}")