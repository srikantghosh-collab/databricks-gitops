from databricks import sql
import os
import subprocess
import re
from ddl_parser import split_sql_statements

print("Starting DDL execution...")

DDL_FILE = "ddl/orders.sql"

# ----------------------------
# Load & parse SQL file
# ----------------------------
if not os.path.exists(DDL_FILE):
    print("DDL file not found — skipping execution")
    exit(0)

with open(DDL_FILE) as f:
    statements = split_sql_statements(f.read())

if not statements:
    print("No DDL statements found — nothing to execute")
    exit(0)

# ----------------------------
# Git commit for audit
# ----------------------------
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
# Execution control
# ----------------------------
backed_up_tables = set()
failed = False
error_msg = None

# ----------------------------
# Execute DDLs one by one
# ----------------------------
for ddl_sql in statements:
    ddl_sql = ddl_sql.strip()
    ddl_upper = ddl_sql.upper()

    try:
        print("\nExecuting DDL:")
        print(ddl_sql)

        # ---------------------------------
        # Detect risky operations
        # ---------------------------------
        if ddl_upper.startswith(("DROP TABLE", "TRUNCATE", "ALTER TABLE")):

            # Safe table name extraction
            match = re.search(
                r"(TABLE|TABLE IF EXISTS)\s+([^\s;]+)",
                ddl_sql,
                re.IGNORECASE
            )

            if not match:
                raise Exception("Unable to detect table name safely")

            table_name = match.group(2)

            # Backup only once per table
            if table_name not in backed_up_tables:
                print(f"Taking backup for table: {table_name}")

                subprocess.check_call(
                    ["python", "scripts/backup_before_drop.py"],
                    env={**os.environ, "DDL_TABLE_NAME": table_name},
                )

                backed_up_tables.add(table_name)

            # Explicit warning for TRUNCATE
            if ddl_upper.startswith("TRUNCATE"):
                print("⚠ TRUNCATE detected — rollback requires restore from backup")

        # ---------------------------------
        # Execute DDL
        # ---------------------------------
        cursor.execute(ddl_sql)

        # ---------------------------------
        # Audit SUCCESS
        # ---------------------------------
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

        # ---------------------------------
        # Audit FAILURE
        # ---------------------------------
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
        break   # 🔥 FAIL FAST

# ----------------------------
# Cleanup
# ----------------------------
cursor.close()
conn.close()

if failed:
    raise Exception(f"DDL execution stopped due to failure: {error_msg}")

print("\nAll DDL statements executed safely")
