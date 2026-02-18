import subprocess
import json
import sys
import os
import re

print(" Detecting DDL changes (diff-based)...")

DDL_FILE = "ddl/orders.sql"

OUTPUT_PATH = os.path.join(
    os.environ.get("SYSTEM_DEFAULTWORKINGDIRECTORY", "."),
    "ddl_output.json"
)



# Helper: extract added SQL from git diff


def get_added_sql_from_diff(file_path):
    try:
        diff = subprocess.check_output(
            ["git", "diff", "HEAD~1", "HEAD", "--", file_path],
            text=True
        )
    except subprocess.CalledProcessError:
        return ""

    added_lines = []
    for line in diff.splitlines():
        if line.startswith("+") and not line.startswith("+++"):
            added_lines.append(line[1:])

    return "\n".join(added_lines)



# Helper: split SQL into statements


def split_sql_statements(sql_text):
    statements = []
    buffer = ""

    for line in sql_text.splitlines():
        line = line.strip()

        if not line or line.startswith("--"):
            continue

        buffer += " " + line

        # detect semicolon anywhere
        if ";" in line:
            parts = buffer.split(";")
            for part in parts[:-1]:
                stmt = part.strip()
                if stmt:
                    statements.append(stmt)
            buffer = parts[-1]

    return statements




# Helper: extract table name


def extract_table_name(stmt_upper):
    patterns = [
        r"CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+([^\s(]+)",
        r"CREATE\s+TABLE\s+([^\s(]+)",
        r"ALTER\s+TABLE\s+([^\s]+)",
        r"DROP\s+TABLE\s+IF\s+EXISTS\s+([^\s]+)",
        r"DROP\s+TABLE\s+([^\s]+)",
        r"TRUNCATE\s+TABLE\s+([^\s]+)"
    ]

    for pattern in patterns:
        match = re.search(pattern, stmt_upper)
        if match:
            return match.group(1)

    return None



# Step 1: Validate SQL file


if not os.path.exists(DDL_FILE):
    print("⚠ No DDL SQL file found")

    with open(OUTPUT_PATH, "w") as f:
        json.dump({"ddls": [], "is_drop": False}, f, indent=2)

    print("##vso[task.setvariable variable=IS_DROP;isOutput=true]false")
    sys.exit(0)



# Step 2: Read ONLY added SQL


added_sql = get_added_sql_from_diff(DDL_FILE)

if not added_sql.strip():
    print("ℹ No new SQL changes detected")

    with open(OUTPUT_PATH, "w") as f:
        json.dump({"ddls": [], "is_drop": False}, f, indent=2)

    print("##vso[task.setvariable variable=IS_DROP;isOutput=true]false")
    sys.exit(0)


statements = split_sql_statements(added_sql)

ddls = []
counter = 1

for stmt in statements:
    stmt_upper = stmt.upper()

    if stmt_upper.startswith(("CREATE", "ALTER", "DROP", "TRUNCATE")):
        ddls.append({
            "id": f"ddl_{counter}",
            "statement": stmt,
            "type": stmt_upper.split()[0],
            "table": extract_table_name(stmt_upper)
        })
        counter += 1


# -------------------------
# Step 3: No DDL case
# -------------------------

if not ddls:
    print("ℹ No executable DDL found")

    with open(OUTPUT_PATH, "w") as f:
        json.dump({"ddls": [], "is_drop": False}, f, indent=2)

    print("##vso[task.setvariable variable=IS_DROP;isOutput=true]false")
    sys.exit(0)



# Step 4: Detect DROP presence


is_drop = any(d["type"] in ("DROP", "TRUNCATE") for d in ddls)

commit_id = subprocess.check_output(
    ["git", "rev-parse", "HEAD"],
    text=True
).strip()


    
# Write artifact


with open(OUTPUT_PATH, "w") as f:
    json.dump(
        {
            "commit_id": commit_id,
            "file": DDL_FILE,
            "ddls": ddls,
            "is_drop": is_drop
        },
        f,
        indent=2
    )

print(f" {len(ddls)} NEW DDL statement(s) detected")
for d in ddls:
    print(f" - [{d['type']}] {d['statement']}")

print("IS_DROP:", is_drop)
print(f"##vso[task.setvariable variable=IS_DROP;isOutput=true]{str(is_drop).lower()}")
