from databricks import sql
import os
import json
import subprocess

print("Starting DDL execution...")

# Read detected DDL
if not os.path.exists("ddl_output.json"):
    print("No DDL artifact found")
    exit(0)

with open("ddl_output.json") as f:
    data = json.load(f)

ddl_sql = data.get("ddl")

if not ddl_sql:
    print("No DDL to execute")
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

# Backup before DROP
if ddl_sql.upper().startswith("DROP"):
    print("DROP detected — taking backup")

    table_name = ddl_sql.split()[-1].replace(";", "")

    subprocess.check_call(
        ["python", "scripts/backup_before_drop.py"],
        env={**os.environ, "DDL_TABLE_NAME": table_name},
    )

commit_id = subprocess.check_output(
    ["git", "rev-parse", "HEAD"],
    text=True
).strip()

status = "SUCCESS"

try:
    print("Executing DDL:")
    print(ddl_sql)

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
