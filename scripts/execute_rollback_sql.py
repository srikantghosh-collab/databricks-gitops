from databricks import sql
import os
import sys
import subprocess

print("Starting rollback SQL execution...")

# -------------------------------------------------
# Inputs
# -------------------------------------------------
ROLLBACK_SQL_FILE = os.environ.get("ROLLBACK_SQL_FILE")
COMMIT_ID = os.environ.get("COMMIT_ID")

if not ROLLBACK_SQL_FILE or not os.path.exists(ROLLBACK_SQL_FILE):
    print("ERROR: Rollback SQL file not provided or not found")
    sys.exit(1)

if not COMMIT_ID:
    COMMIT_ID = subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        text=True
    ).strip()

# -------------------------------------------------
# Read rollback SQL
# -------------------------------------------------
with open(ROLLBACK_SQL_FILE) as f:
    sql_text = f.read()

statements = [
    stmt.strip()
    for stmt in sql_text.split(";")
    if stmt.strip() and not stmt.strip().startswith("--")
]

if not statements:
    print("No rollback SQL statements to execute")
    sys.exit(0)

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

# -------------------------------------------------
# Execute rollback SQL
# -------------------------------------------------
for stmt in statements:
    try:
        print("\nExecuting rollback SQL:")
        print(stmt)

        cursor.execute(stmt)

        cursor.execute(f"""
            INSERT INTO ddl_audit_log VALUES (
                current_timestamp(),
                '{COMMIT_ID}',
                '{stmt.replace("'", "''")}',
                'ROLLBACK',
                'SUCCESS'
            )
        """)

        print("Rollback audit recorded: SUCCESS")

    except Exception as e:
        cursor.execute(f"""
            INSERT INTO ddl_audit_log VALUES (
                current_timestamp(),
                '{COMMIT_ID}',
                '{stmt.replace("'", "''")}',
                'ROLLBACK',
                'FAILED'
            )
        """)

        print("Rollback failed:", str(e))
        cursor.close()
        conn.close()
        raise Exception("Rollback stopped due to failure")

# -------------------------------------------------
# Cleanup
# -------------------------------------------------
cursor.close()
conn.close()

print("\nRollback executed successfully")
