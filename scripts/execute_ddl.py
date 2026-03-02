from databricks import sql
import os
import json
import re
import sys
import subprocess

print("Starting DDL execution...")
is_revert = os.environ.get("PIPELINE_IS_REVERT", "no") == "yes"

if is_revert:
    print("Git revert detected → skipping Execute DDL & backups")
    sys.exit(0)


DDL_ARTIFACT = "ddl_output.json"

# -------------------------------------------------
# Load DDL artifact
# -------------------------------------------------
if not os.path.exists(DDL_ARTIFACT):
    print("DDL artifact not found — skipping execution")
    sys.exit(0)

with open(DDL_ARTIFACT) as f:
    payload = json.load(f)

ddls = payload.get("ddls", [])
if not ddls:
    print("No DDL statements to execute — exiting")
    sys.exit(0)

commit_id = payload.get("commit_id") or subprocess.check_output(
    ["git", "rev-parse", "HEAD"], text=True
).strip()

rollback_type = os.environ.get("ROLLBACK_TYPE", "NONE")
is_drop = os.environ.get("IS_DROP", "false") == "true"

print(f"Rollback type: {rollback_type}")
print(f"Is drop: {is_drop}")

# -------------------------------------------------
# Connect to Databricks
# -------------------------------------------------
conn = sql.connect(
    server_hostname=os.environ["DATABRICKS_HOST"],
    http_path=os.environ["DATABRICKS_HTTP_PATH"],
    access_token=os.environ["DATABRICKS_TOKEN"],
)

cursor = conn.cursor()
cursor.execute("USE CATALOG hive_metastore")
cursor.execute("USE SCHEMA default")
print("Catalog & schema set")

# =================================================
# Helpers
# =================================================
def extract_table_name(ddl_sql):
    patterns = [
        r"CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+([^\s(]+)",
        r"CREATE\s+TABLE\s+([^\s(]+)",
        r"ALTER\s+TABLE\s+([^\s;]+)",
        r"DROP\s+TABLE\s+IF\s+EXISTS\s+([^\s;]+)",
        r"DROP\s+TABLE\s+([^\s;]+)"
    ]
    for p in patterns:
        m = re.search(p, ddl_sql, re.IGNORECASE)
        if m:
            return m.group(1)
    return None

def needs_column_mapping(ddl_upper: str) -> bool:
    patterns = [
        "RENAME COLUMN",
        "CHANGE COLUMN",
        "DROP COLUMN",
        "REPLACE COLUMNS",
        "ALTER COLUMN",
    ]

    # reorder cases
    if "ALTER COLUMN" in ddl_upper and (" FIRST" in ddl_upper or " AFTER " in ddl_upper):
        return True

    return any(p in ddl_upper for p in patterns)
# Column mapping Auto enabler

def ensure_column_mapping_enabled(cursor, table_name):
    try:
        cursor.execute(f"SHOW TBLPROPERTIES {table_name}")
        props = {row[0]: row[1] for row in cursor.fetchall()}
        mode = props.get("delta.columnMapping.mode")

        if mode == "name":
            print(f"Column mapping already enabled for {table_name}")
            return

        print(f"Enabling column mapping for {table_name}...")

        cursor.execute(f"""
            ALTER TABLE {table_name}
            SET TBLPROPERTIES ('delta.columnMapping.mode' = 'name')
        """)

        print(f"Column mapping enabled for {table_name}")

    except Exception as e:
        print(f"Failed to enable column mapping: {e}")
        raise

# =================================================
# Decide BACKUP MODE (ONCE PER COMMIT)
# =================================================
ddl_text = " ".join(d["statement"].upper() for d in ddls)

if any(
    kw in ddl_text
    for kw in [
        "DROP TABLE",
        "DROP COLUMN",
        "CHANGE COLUMN",
        "ALTER COLUMN",
        "TYPE",
    ]
):
    backup_mode = "DATA_BACKUP"

elif "ALTER TABLE" in ddl_text:
    backup_mode = "STATE_BACKUP"

else:
    backup_mode = "NONE"


print(f"Backup mode selected: {backup_mode}")

# =================================================
# Perform backup BEFORE execution
# =================================================
backed_up_tables = {}

if backup_mode != "NONE":
    # collect DDLs per table so we can provide the specific ddl_sql when doing state backups
    for item in ddls:
        table_name = extract_table_name(item["statement"])
        if table_name:
            ddl_stmt = item["statement"].strip()
            backed_up_tables.setdefault(table_name, []).append(ddl_stmt)

    if backup_mode == "DATA_BACKUP":
        for table in backed_up_tables.keys():
            print(f"DATA_BACKUP → {table}")
            subprocess.check_call(
                ["python", "scripts/backup_before_drop.py"],
                env={**os.environ, "DDL_TABLE_NAME": table, "COMMIT_ID": commit_id},
            )

    elif backup_mode == "STATE_BACKUP":
     for table, ddl_list in backed_up_tables.items():
        ddl_sql = ddl_list[-1]   
        print(f"STATE_BACKUP (single) → {table}")

        subprocess.check_call(
            ["python", "scripts/capture_table_state.py"],
            env={
                **os.environ,
                "TABLE_NAME": table,
                "DDL_SQL": ddl_sql,
                "COMMIT_ID": commit_id
            },
        )

# =================================================
# Execute DDLs
# =================================================
failed = False
error_msg = None

for item in ddls:
    ddl_sql = item["statement"].strip()
    ddl_upper = ddl_sql.upper()

    table_name = extract_table_name(ddl_sql)
    try:

        if table_name and needs_column_mapping(ddl_upper):
            ensure_column_mapping_enabled(cursor, table_name)

        print("\nExecuting DDL:")
        print(ddl_sql)
        cursor.execute(ddl_sql)

        cursor.execute(f"""
            INSERT INTO ddl_audit_log VALUES (
                current_timestamp(),
                '{commit_id}',
                '{ddl_sql.replace("'", "''")}',
                'EXECUTE',
                'SUCCESS'
            )
        """)
    except Exception as e:
        failed = True
        error_msg = str(e)
        break
from databricks import sql
import os
import json
import re
import sys
import subprocess

print("Starting DDL execution...")
is_revert = os.environ.get("PIPELINE_IS_REVERT", "no") == "yes"

if is_revert:
    print("Git revert detected → skipping Execute DDL & backups")
    sys.exit(0)

DDL_ARTIFACT = "ddl_output.json"

# -------------------------------------------------
# Load DDL artifact
# -------------------------------------------------
if not os.path.exists(DDL_ARTIFACT):
    print("DDL artifact not found — skipping execution")
    sys.exit(0)

with open(DDL_ARTIFACT) as f:
    payload = json.load(f)

ddls = payload.get("ddls", [])
if not ddls:
    print("No DDL statements to execute — exiting")
    sys.exit(0)

commit_id = payload.get("commit_id") or subprocess.check_output(
    ["git", "rev-parse", "HEAD"], text=True
).strip()

rollback_type = os.environ.get("ROLLBACK_TYPE", "NONE")
is_drop = os.environ.get("IS_DROP", "false") == "true"

print(f"Rollback type: {rollback_type}")
print(f"Is drop: {is_drop}")

# -------------------------------------------------
# Connect to Databricks
# -------------------------------------------------
conn = sql.connect(
    server_hostname=os.environ["DATABRICKS_HOST"],
    http_path=os.environ["DATABRICKS_HTTP_PATH"],
    access_token=os.environ["DATABRICKS_TOKEN"],
)

cursor = conn.cursor()
cursor.execute("USE CATALOG hive_metastore")
cursor.execute("USE SCHEMA default")
print("Catalog & schema set")

# =================================================
# 🔒 DIALECT VALIDATOR
# =================================================
UNSUPPORTED_KEYWORDS = [
    "ALTER INDEX",
    "SEQUENCE",
    "TRIGGER",
    "TABLESPACE",
    "ATTACH PARTITION",
    "DETACH PARTITION",
    "ALTER DATABASE",
    "ENABLE ROW LEVEL SECURITY",
    "UNLOGGED",
    "SWITCH TO",
    "ALTER TYPE"
]

def validate_sql_dialect(ddl_sql):
    ddl_upper = ddl_sql.upper()
    for kw in UNSUPPORTED_KEYWORDS:
        if kw in ddl_upper:
            raise Exception(f"Unsupported SQL for Databricks Delta: {kw}")

# =================================================
# 🔍 DDL ANALYZER
# =================================================
def classify_ddl(ddl_sql):
    ddl_upper = ddl_sql.upper()

    if "ALTER TABLE" in ddl_upper and "ALTER COLUMN" in ddl_upper and "TYPE" in ddl_upper:
        return "ALTER_TYPE"

    if "DROP TABLE" in ddl_upper:
        return "DROP_TABLE"

    if "ADD COLUMN" in ddl_upper:
        return "ADD_COLUMN"

    if "DROP COLUMN" in ddl_upper:
        return "DROP_COLUMN"

    return "OTHER"

# =================================================
# TYPE HELPERS
# =================================================
def parse_alter_type(ddl_sql):
    pattern = r"ALTER TABLE\s+(\S+)\s+ALTER COLUMN\s+(\S+)\s+TYPE\s+(.+)"
    match = re.search(pattern, ddl_sql, re.IGNORECASE)
    if match:
        return match.group(1), match.group(2), match.group(3).strip()
    return None, None, None

def extract_decimal(type_str):
    match = re.search(r"DECIMAL\((\d+),\s*(\d+)\)", type_str.upper())
    if match:
        return int(match.group(1)), int(match.group(2))
    return None, None

def is_widening_change(old_type, new_type):
    old_type = old_type.upper()
    new_type = new_type.upper()

    if old_type == new_type:
        return True

    if old_type == "INT" and new_type == "BIGINT":
        return True

    if old_type.startswith("DECIMAL") and new_type.startswith("DECIMAL"):
        old_p, old_s = extract_decimal(old_type)
        new_p, new_s = extract_decimal(new_type)
        if old_p and new_p:
            return new_p >= old_p and new_s == old_s

    if old_type == "INT" and new_type == "STRING":
        return True

    return False

def get_column_type(cursor, table, column):
    cursor.execute(f"DESCRIBE TABLE {table}")
    for row in cursor.fetchall():
        if row[0].lower() == column.lower():
            return row[1]
    return None

def generate_migration_sql(table, column, new_type):
    tmp_col = f"{column}__tmp"
    return [
        f"ALTER TABLE {table} ADD COLUMN {tmp_col} {new_type}",
        f"UPDATE {table} SET {tmp_col} = CAST({column} AS {new_type})",
        f"ALTER TABLE {table} DROP COLUMN {column}",
        f"ALTER TABLE {table} RENAME COLUMN {tmp_col} TO {column}"
    ]

# =================================================
# EXECUTION LOOP
# =================================================
failed = False
error_msg = None

for item in ddls:
    ddl_sql = item["statement"].strip()
    ddl_upper = ddl_sql.upper()

    try:
        validate_sql_dialect(ddl_sql)

        ddl_type = classify_ddl(ddl_sql)

        print("\nExecuting DDL:")
        print(ddl_sql)

        if ddl_type == "ALTER_TYPE":
            table, column, new_type = parse_alter_type(ddl_sql)

            old_type = get_column_type(cursor, table, column)
            print(f"Old type: {old_type}, New type: {new_type}")

            if is_widening_change(old_type, new_type):
                cursor.execute(ddl_sql)
            else:
                print("Unsupported direct type change → running safe migration")
                migration_sql = generate_migration_sql(table, column, new_type)
                for stmt in migration_sql:
                    print(f"Executing: {stmt}")
                    cursor.execute(stmt)

        else:
            cursor.execute(ddl_sql)

        cursor.execute(f"""
            INSERT INTO ddl_audit_log VALUES (
                current_timestamp(),
                '{commit_id}',
                '{ddl_sql.replace("'", "''")}',
                'EXECUTE',
                'SUCCESS'
            )
        """)

    except Exception as e:
        failed = True
        error_msg = str(e)
        break

cursor.close()
conn.close()

if failed:
    raise Exception(f"DDL execution stopped due to failure: {error_msg}")

print("\nAll DDL statements executed successfully")
cursor.close()
conn.close()

if failed:
    raise Exception(f"DDL execution stopped due to failure: {error_msg}")

print("\nAll DDL statements executed successfully")