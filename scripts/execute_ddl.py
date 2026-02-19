from databricks import sql
import os
import subprocess
import json
import re
import sys

print("Starting DDL execution...")

DDL_ARTIFACT = "ddl_output.json"


# Load DDL artifact

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
    ["git", "rev-parse", "HEAD"],
    text=True
).strip()


# Connect to Databricks

conn = sql.connect(
    server_hostname=os.environ["DATABRICKS_HOST"],
    http_path=os.environ["DATABRICKS_HTTP_PATH"],
    access_token=os.environ["DATABRICKS_TOKEN"],
)

cursor = conn.cursor()
cursor.execute("USE CATALOG hive_metastore")
cursor.execute("USE SCHEMA default")
print("Catalog & schema set")

# 🔹 HELPER FUNCTIONS 


def extract_table_name(ddl_sql):
    patterns = [
        r"DROP\s+TABLE\s+IF\s+EXISTS\s+([^\s;]+)",
        r"DROP\s+TABLE\s+([^\s;]+)",
        r"TRUNCATE\s+TABLE\s+([^\s;]+)",
        r"ALTER\s+TABLE\s+([^\s;]+)"
    ]
    for p in patterns:
        m = re.search(p, ddl_sql, re.IGNORECASE)
        if m:
            return m.group(1)
    return None


def is_destructive_alter(ddl_upper):
    destructive_ops = [
        "DROP COLUMN",
        "RENAME COLUMN",
        "ALTER COLUMN",
        "CHANGE COLUMN"
    ]
    return any(op in ddl_upper for op in destructive_ops)


def ensure_column_mapping(cursor, table_name):
    """
    Auto-enable column mapping mode 'name' if not already enabled
    Required for RENAME COLUMN in Delta tables
    """
    cursor.execute(f"SHOW TBLPROPERTIES {table_name}")
    props = {row[0]: row[1] for row in cursor.fetchall()}

    if props.get("delta.columnMapping.mode") != "name":
        print(f"Enabling column mapping for table: {table_name}")
        cursor.execute(
            f"ALTER TABLE {table_name} "
            "SET TBLPROPERTIES ('delta.columnMapping.mode'='name')"
        )


# 🔹 EXECUTION CONTROL


backed_up_tables = set()
failed = False
error_msg = None


#  EXECUTE DDL STATEMENTS


for item in ddls:
    ddl_sql = item["statement"].strip()
    ddl_upper = ddl_sql.upper()

    try:
        print("\nExecuting DDL:")
        print(ddl_sql)

        table_name = extract_table_name(ddl_sql)
        need_backup = False

        
        # Backup logic
        

        # DROP / TRUNCATE → always backup
        if ddl_upper.startswith(("DROP", "TRUNCATE")):
            need_backup = True

        # ALTER → backup only if destructive
        elif ddl_upper.startswith("ALTER") and is_destructive_alter(ddl_upper):
            need_backup = True

        if need_backup and table_name:
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

        
        # Auto-enable column mapping before rename
        
        if "RENAME COLUMN" in ddl_upper and table_name:
            ensure_column_mapping(cursor, table_name)

        
        # Execute DDL
        
        cursor.execute(ddl_sql)

        
        # Audit SUCCESS
        
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


# Cleanup

cursor.close()
conn.close()

if failed:
    raise Exception(f"DDL execution stopped due to failure: {error_msg}")

print("\nAll DDL statements executed successfully")
