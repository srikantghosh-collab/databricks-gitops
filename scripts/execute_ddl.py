from databricks import sql
import os
import json
import re
import sys
import subprocess

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

# Rollback decision from AI stage
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
# Helper functions
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


# =================================================
# Execute DDLs
# =================================================

backed_up_tables = set()
failed = False
error_msg = None

for item in ddls:
    ddl_sql = item["statement"].strip()
    ddl_upper = ddl_sql.upper()
    table_name = extract_table_name(ddl_sql)

    try:
        print("\nExecuting DDL:")
        print(ddl_sql)

        # -----------------------------------------
        # Backup decision (AI driven)
        # -----------------------------------------
        need_backup = False

        if ddl_upper.startswith("DROP TABLE"):
            need_backup = True
        elif ddl_upper.startswith("ALTER TABLE") and rollback_type in ("PARTIAL", "IRREVERSIBLE"):
            need_backup = True

        if need_backup:
            if not table_name:
                raise Exception("Backup required but table name could not be determined")

            if table_name not in backed_up_tables:
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
                print(f"Backup completed for table: {table_name}")

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