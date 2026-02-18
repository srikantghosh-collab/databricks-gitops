from databricks import sql
import os
import subprocess
import json
import re
import sys

print("Starting DDL execution...")

DDL_ARTIFACT = "ddl_output.json"

# ----------------------------
# Load DDL artifact
# ----------------------------
if not os.path.exists(DDL_ARTIFACT):
    print("DDL artifact not found — skipping execution")
    sys.exit(0)

with open(DDL_ARTIFACT) as f:
    payload = json.load(f)

ddls = payload.get("ddls", [])

if not ddls:
    print("No DDL statements to execute — exiting")
    sys.exit(0)

commit_id = payload.get("commit_id")

if not commit_id:
    commit_id = subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        text=True
    ).strip()

# ----------------------------
# Connect to Databricks
# ----------------------------
conn = sql.connect(
    server_hostname=os.environ["DATABRICKS_HOST"],
    http_path=os.environ["DATABRICKS_HTTP_PATH"],
    access_token=os.environ["DATABRICKS_TOKEN"],
)

cursor = conn.cursor()
cursor.execute("USE CATALOG hive_metastore")
cursor.execute("USE SCHEMA default")

print("Catalog & schema set")

# ----------------------------
# Helper: extract table name
# ----------------------------
def extract_table_name(ddl_sql):
    patterns = [
        r"DROP\s+TABLE\s+IF\s+EXISTS\s+([^\s;]+)",
        r"DROP\s+TABLE\s+([^\s;]+)",
        r"TRUNCATE\s+TABLE\s+([^\s;]+)",
        r"ALTER\s+TABLE\s+([^\s;]+)"
    ]
    for pattern in patterns:
        match = re.search(pattern, ddl_sql, re.IGNORECASE)
        if match:
            return match.group(1)
    return None

# ----------------------------
# Execution control
# ----------------------------
backed_up_tables = set()
failed = False
error_msg = None

# ----------------------------
# Execute each DDL
# ----------------------------
for item in ddls:
    ddl_sql = item["statement"].strip()
    ddl_upper = ddl_sql.upper()

    try:
        print("\nExecuting DDL:")
        print(ddl_sql)

        # ----------------------------
        # Backup before risky ops
        # ----------------------------
        if ddl_upper.startswith(("DROP", "TRUNCATE", "ALTER")):

            table_name = extract_table_name(ddl_sql)

            if not table_name:
                raise Exception("Unable to extract table name safely")

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

            if ddl_upper.startswith("TRUNCATE"):
                print("⚠ TRUNCATE detected — rollback requires restore")

        # ----------------------------
        # Execute DDL
        # ----------------------------
        cursor.execute(ddl_sql)

        # ----------------------------
        # Audit SUCCESS
        # ----------------------------
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
        break  # fail fast

# ----------------------------
# Cleanup
# ----------------------------
cursor.close()
conn.close()

if failed:
    raise Exception(f"DDL execution stopped due to failure: {error_msg}")

print("\nAll DDL statements executed successfully")
