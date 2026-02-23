import os
import glob
from databricks import sql
import sys

print("Starting rollback restore process...")

# ----------------------------------------
# Locate rollback SQL file
# ----------------------------------------
rollback_files = glob.glob("rollback_*.sql")

if not rollback_files:
    print("Rollback SQL file not found")
    sys.exit(1)

rollback_file = rollback_files[0]
print(f"Using rollback file: {rollback_file}")

with open(rollback_file) as f:
    rollback_sql = f.read()

# ----------------------------------------
# Read rollback type
# ----------------------------------------
rollback_type = os.environ.get("ROLLBACK_TYPE", "NONE")
print(f"Rollback type: {rollback_type}")

# ----------------------------------------
# Connect to Databricks
# ----------------------------------------
conn = sql.connect(
    server_hostname=os.environ["DATABRICKS_HOST"],
    http_path=os.environ["DATABRICKS_HTTP_PATH"],
    access_token=os.environ["DATABRICKS_TOKEN"],
)

cursor = conn.cursor()
cursor.execute("USE CATALOG hive_metastore")
cursor.execute("USE SCHEMA default")

# ----------------------------------------
# Restore logic based on rollback type
# ----------------------------------------
if rollback_type in ("PARTIAL", "IRREVERSIBLE"):

    original_table = os.environ.get("ORIGINAL_TABLE")
    backup_table = os.environ.get("BACKUP_TABLE")

    if not original_table or not backup_table:
        print("ORIGINAL_TABLE or BACKUP_TABLE env var not set")
        sys.exit(1)

    print(f"Restoring table `{original_table}` from backup `{backup_table}`")

    cursor.execute(f"DROP TABLE IF EXISTS {original_table}")
    cursor.execute(
        f"CREATE TABLE {original_table} DEEP CLONE {backup_table}"
    )

    print("Table restored using DEEP CLONE")

# ----------------------------------------
# Execute rollback SQL if needed
# ----------------------------------------
if rollback_type in ("REVERSIBLE", "PARTIAL"):

    print("Executing rollback SQL statements...")

    # Split statements safely
    statements = [
        s.strip()
        for s in rollback_sql.split(";")
        if s.strip() and not s.strip().startswith("--")
    ]

    for stmt in statements:
        print(f"Executing: {stmt}")
        cursor.execute(stmt)

    print("Rollback SQL executed successfully")

# ----------------------------------------
# Cleanup
# ----------------------------------------
cursor.close()
conn.close()

print("Rollback completed successfully")