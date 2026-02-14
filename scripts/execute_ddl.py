from databricks import sql
import os
import subprocess
from ddl_parser import parse_sql_file

print("Starting DDL execution...")

DDL_FILE = "ddl/orders.sql"

if not os.path.exists(DDL_FILE):
    print("DDL file not found")
    exit(0)

# Parse multiple DDL statements
statements = parse_sql_file(DDL_FILE)

if not statements:
    print("No DDL statements found")
    exit(0)

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

commit_id = subprocess.check_output(
    ["git", "rev-parse", "HEAD"],
    text=True
).strip()

# Execute each DDL separately
for ddl_sql in statements:

    status = "SUCCESS"

    try:
        print("\nExecuting DDL:")
        print(ddl_sql)

        # Backup before DROP
        if ddl_sql.upper().startswith("DROP TABLE"):
            table_name = ddl_sql.split()[2]

            print("DROP detected — taking backup")

            subprocess.check_call(
                ["python", "scripts/backup_before_drop.py"],
                env={**os.environ, "DDL_TABLE_NAME": table_name},
            )

        cursor.execute(ddl_sql)

    except Exception as e:
        print("DDL execution failed:", str(e))
        status = "FAILED"
        raise

    finally:
        audit_sql = f"""
        INSERT INTO ddl_audit_log VALUES (
          current_timestamp(),
          '{commit_id}',
          '{ddl_sql.replace("'", "''")}',
          'EXECUTE',
          '{status}'
        )
        """

        cursor.execute(audit_sql)
        print("Audit log recorded")

cursor.close()
conn.close()

print("All DDL statements executed successfully")
