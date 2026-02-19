import json
import sys
import os
import subprocess

print("Detecting DDL changes ")

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


if not os.path.exists(DDL_FILE):
    print("No DDL SQL file found")
    json.dump({"ddls": [], "is_drop": False}, open(OUTPUT_PATH, "w"))
    print("##vso[task.setvariable variable=IS_DROP;isOutput=true]false")
    sys.exit(0)


with open(DDL_FILE) as f:
    sql_text = f.read()

statements = split_sql_statements(sql_text)

DDL_PREFIXES = ("CREATE", "ALTER", "DROP", "TRUNCATE")
ddls = []
counter = 1

for stmt in statements:
    if stmt.upper().startswith(DDL_PREFIXES):
        ddls.append({
            "id": f"ddl_{counter}",
            "statement": stmt,
            "type": stmt.split()[0].upper()
        })
        counter += 1

if not ddls:
    print("NO executable DDL found")
    json.dump({"ddls": [], "is_drop": False}, open(OUTPUT_PATH, "w"))
    print("##vso[task.setvariable variable=IS_DROP;isOutput=true]false")
    sys.exit(0)

is_drop = any(d["type"] in ("DROP", "TRUNCATE") for d in ddls)

commit_id = subprocess.check_output(
    ["git", "rev-parse", "HEAD"], text=True
).strip()

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
