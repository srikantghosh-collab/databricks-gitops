from databricks import sql
import os
import sys

print("Starting rollback restore process ")

REVERT_COMMIT = os.environ.get("REVERT_COMMIT")
if not REVERT_COMMIT:
    print("REVERT_COMMIT not provided")
    sys.exit(1)

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

# =====================================================
# 1️⃣ Try DATA restore first (DROP TABLE case)
# =====================================================
print("Checking DATA_BACKUP table...")

cursor.execute(f"""
SELECT source_table, backup_table
FROM ddl_data_backup
WHERE commit_id = '{REVERT_COMMIT}'
ORDER BY backup_time DESC
LIMIT 1
""")

row = cursor.fetchone()

if row:
    source_table, backup_table = row
    print(f"DATA_BACKUP found → restoring {source_table} from {backup_table}")

    cursor.execute(f"DROP TABLE IF EXISTS {source_table}")
    cursor.execute(
        f"CREATE TABLE {source_table} DEEP CLONE {backup_table}"
    )

    print("DATA restore completed successfully")
    cursor.close()
    conn.close()
    sys.exit(0)

# =====================================================
# 2️⃣ Try STATE restore (ALTER / PROPERTIES)
# =====================================================
print("No DATA_BACKUP found → checking STATE_BACKUP table...")

cursor.execute(f"""
SELECT rollback_sql
FROM ddl_state_backup
WHERE commit_id = '{REVERT_COMMIT}'
ORDER BY backup_time DESC
LIMIT 1
""")

row = cursor.fetchone()

if row:
    rollback_sql = row[0]
    print("STATE_BACKUP found → executing rollback SQL")
    print(rollback_sql)

    statements = [
        s.strip()
        for s in rollback_sql.split(";")
        if s.strip()
    ]

    for stmt in statements:
        print(f"Executing: {stmt}")
        cursor.execute(stmt)

    print("STATE restore completed successfully")
    cursor.close()
    conn.close()
    sys.exit(0)

# =====================================================
# 3️⃣ Nothing to rollback
# =====================================================
print("No rollback data found → nothing to restore")

cursor.close()
conn.close()
print("Rollback finished (no-op)")