from databricks import sql
import os
import subprocess
import json
import re
import sys

print("Starting DDL execution...")

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
# Helper functions
# =================================================

def extract_table_name(ddl_sql):
    patterns = [
        r"CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+([^\s(]+)",
        r"CREATE\s+TABLE\s+([^\s(]+)",
        r"ALTER\s+TABLE\s+([^\s;]+)",
        r"DROP\s+TABLE\s+IF\s+EXISTS\s+([^\s;]+)",
        r"DROP\s+TABLE\s+([^\s;]+)",
        r"TRUNCATE\s+TABLE\s+([^\s;]+)"
    ]
    for p in patterns:
        m = re.search(p, ddl_sql, re.IGNORECASE)
        if m:
            return m.group(1)
    return None


def is_destructive_alter(ddl_upper):
    return any(op in ddl_upper for op in [
        "DROP COLUMN",
        "RENAME COLUMN",
        "ALTER COLUMN",
        "CHANGE COLUMN"
    ])


def ensure_column_mapping(cursor, table_name):
    cursor.execute(f"SHOW TBLPROPERTIES {table_name}")
    props = {row[0]: row[1] for row in cursor.fetchall()}

    needs_upgrade = (
        props.get("delta.columnMapping.mode") != "name"
        or int(props.get("delta.minReaderVersion", 0)) < 2
        or int(props.get("delta.minWriterVersion", 0)) < 5
    )

    if needs_upgrade:
        print(f"Enabling column mapping + protocol upgrade for {table_name}")
        cursor.execute(f"""
            ALTER TABLE {table_name}
            SET TBLPROPERTIES (
                'delta.columnMapping.mode' = 'name',
                'delta.minReaderVersion' = '2',
                'delta.minWriterVersion' = '5'
            )
        """)


def inject_column_mapping_on_create(ddl_sql):
    ddl_upper = ddl_sql.upper()
    if ddl_upper.startswith("CREATE TABLE") and "TBLPROPERTIES" not in ddl_upper:
        return ddl_sql.rstrip(";") + \
            " TBLPROPERTIES ('delta.columnMapping.mode'='name');"
    return ddl_sql

# =================================================
# Execution control
# =================================================

backed_up_tables = set()
failed = False
error_msg = None

# =================================================
# Execute DDLs
# =================================================

for item in ddls:
    ddl_sql = item["statement"].strip()
    ddl_upper = ddl_sql.upper()
    table_name = extract_table_name(ddl_sql)

    try:
        print("\nExecuting DDL:")
        print(ddl_sql)

        # -----------------------------------------
        # CREATE TABLE → inject column mapping
        # -----------------------------------------
        if ddl_upper.startswith("CREATE TABLE"):
            ddl_sql = inject_column_mapping_on_create(ddl_sql)

        # -----------------------------------------
        # 🔥 TBLPROPERTIES SNAPSHOT (IMPORTANT)
        # -----------------------------------------
        if (
            ddl_upper.startswith("ALTER TABLE")
            and "SET TBLPROPERTIES" in ddl_upper
            and table_name
        ):
            print(f"Capturing TBLPROPERTIES snapshot for {table_name}")
            subprocess.check_call(
                ["python", "scripts/capture_tblproperties_snapshot_sql.py"],
                env={
                    **os.environ,
                    "TABLE_NAME": table_name,
                    "COMMIT_ID": commit_id
                }
            )

        # -----------------------------------------
        # Backup logic (table-level rollback)
        # -----------------------------------------
        need_backup = False
        if ddl_upper.startswith(("DROP", "TRUNCATE")):
            need_backup = True
        elif ddl_upper.startswith("ALTER") and is_destructive_alter(ddl_upper):
            need_backup = True

        if need_backup and table_name and table_name not in backed_up_tables:
            print(f"Taking backup for table: {table_name}")
            subprocess.check_call(
                ["python", "scripts/backup_before_drop.py"],
                env={**os.environ, "DDL_TABLE_NAME": table_name},
            )
            subprocess.check_call(
                ["python", "scripts/upload_rollback_metadata.py"],
                env={**os.environ, "COMMIT_ID": commit_id},
            )
            backed_up_tables.add(table_name)

        # -----------------------------------------
        # Ensure column mapping for destructive ALTER
        # -----------------------------------------
        if is_destructive_alter(ddl_upper) and table_name:
            ensure_column_mapping(cursor, table_name)

        # -----------------------------------------
        # Execute DDL
        # -----------------------------------------
        cursor.execute(ddl_sql)

        # -----------------------------------------
        # Audit SUCCESS
        # -----------------------------------------
        cursor.execute(f"""
            INSERT INTO ddl_audit_log VALUES (
                current_timestamp(),
                '{commit_id}',
                '{ddl_sql.replace("'", "''")}',
                'EXECUTE',
                'SUCCESS'
            )
        """)
        print("Audit log recorded: SUCCESS")

    except Exception as e:
        failed = True
        error_msg = str(e)
        cursor.execute(f"""
            INSERT INTO ddl_audit_log VALUES (
                current_timestamp(),
                '{commit_id}',
                '{ddl_sql.replace("'", "''")}',
                'EXECUTE',
                'FAILED'
            )
        """)
        print("Audit log recorded: FAILED")
        print("DDL execution failed:", error_msg)
        break

# =================================================
# Cleanup
# =================================================

cursor.close()
conn.close()

if failed:
    raise Exception(f"DDL execution stopped due to failure: {error_msg}")

print("\nAll DDL statements executed successfully")
