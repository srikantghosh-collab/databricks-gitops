from databricks import sql
import os
import subprocess
import re
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

# Ensure audit table exists
cursor.execute("""
CREATE TABLE IF NOT EXISTS ddl_audit_log (
  timestamp TIMESTAMP,
  commit_id STRING,
  ddl_statement STRING,
  action STRING,
  status STRING
)
USING DELTA
""")

commit_id = subprocess.check_output(
    ["git", "rev-parse", "HEAD"],
    text=True
).strip()

overall_failure = False

# Execute each DDL separately
for ddl_sql in statements:

    status = "SUCCESS"

    try:
        print("\nExecuting DDL:")
        print(ddl_sql)

        ddl_upper = ddl_sql.upper()

        # -----------------------------
        # Backup before DROP
        # -----------------------------
        if ddl_upper.startswith("DROP TABLE"):

            match = re.search(
                r"DROP TABLE\s+(IF EXISTS\s+)?([^\s;]+)",
                ddl_sql,
                re.IGNORECASE
            )

            if match:
                table_name = match.group(2)
                print(f"DROP detected — taking backup of {table_name}")

                subprocess.check_call(
                    ["python", "scripts/backup_before_drop.py"],
                    env={**os.environ, "DDL_TABLE_NAME": table_name},
                )

        # Execute statement
        cursor.execute(ddl_sql)

    except Exception as e:
        print("DDL execution failed:", str(e))
        status = "FAILED"
        overall_failure = True

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

        try:
            cursor.execute(audit_sql)
            print("Audit log recorded")
        except Exception as audit_error:
            print("Audit logging failed:", audit_error)

# Cleanup
cursor.close()
conn.close()

if overall_failure:
    raise Exception("One or more DDL statements failed")

print("All DDL statements executed")
