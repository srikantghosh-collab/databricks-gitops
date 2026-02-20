import os
import glob
from databricks import sql
import sys

print("Starting rollback restore process...")

# ----------------------------
# Locate rollback SQL file
# ----------------------------
rollback_files = glob.glob("rollback_*.sql")

if not rollback_files:
    print(" Rollback SQL file not found")
    sys.exit(1)

rollback_file = rollback_files[0]
print(f"Using rollback file: {rollback_file}")

with open(rollback_file) as f:
    rollback_sql = f.read()


# Block unsupported ALTER rollback

if "MANUAL INTERVENTION REQUIRED" in rollback_sql.upper():
    print(" Rollback requires manual intervention.")
    print("Rollback SQL contains advisory comments only.")
    sys.exit(1)

# ----------------------------
# Required env vars
# ----------------------------
original_table = os.environ.get("ORIGINAL_TABLE")
backup_table = os.environ.get("BACKUP_TABLE")

if not original_table or not backup_table:
    print(" ORIGINAL_TABLE or BACKUP_TABLE env var not set")
    sys.exit(1)

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

# ----------------------------
# Step 1: Restore table from backup
# ----------------------------
print(f"Restoring table `{original_table}` from backup `{backup_table}`")

cursor.execute(f"DROP TABLE IF EXISTS {original_table}")
cursor.execute(f"""
    CREATE TABLE {original_table}
    AS SELECT * FROM {backup_table}
""")

print(" Table restored from backup")

# ----------------------------
# Step 2: Execute rollback SQL
# ----------------------------
print("Executing rollback SQL...")
cursor.execute(rollback_sql)

print(" Rollback SQL executed successfully")

# ----------------------------
# Cleanup
# ----------------------------
cursor.close()
conn.close()

print(" Rollback completed successfully")
