from databricks import sql
import os
import sys

print("Starting STATE rollback (table metadata restore)...")

# -------------------------------------------------
# Required env vars
# -------------------------------------------------
REVERT_COMMIT = os.environ.get("REVERT_COMMIT")

if not REVERT_COMMIT:
    raise Exception("REVERT_COMMIT environment variable not set")

CATALOG = "hive_metastore"
SCHEMA = "default"
STATE_TABLE = "ddl_state_backup"

print(f"Reverting state for commit: {REVERT_COMMIT}")

# -------------------------------------------------
# Connect to Databricks
# -------------------------------------------------
conn = sql.connect(
    server_hostname=os.environ["DATABRICKS_HOST"],
    http_path=os.environ["DATABRICKS_HTTP_PATH"],
    access_token=os.environ["DATABRICKS_TOKEN"],
)

cursor = conn.cursor()
cursor.execute(f"USE CATALOG {CATALOG}")
cursor.execute(f"USE SCHEMA {SCHEMA}")

# -------------------------------------------------
# Fetch restore SQL (LATEST FIRST)
# -------------------------------------------------
fetch_sql = f"""
SELECT
    table_name,
    restore_sql
FROM {STATE_TABLE}
WHERE commit_id = '{REVERT_COMMIT}'
ORDER BY captured_at DESC
"""

cursor.execute(fetch_sql)
rows = cursor.fetchall()

if not rows:
    print("No state backup found for this commit. Nothing to restore.")
    cursor.close()
    conn.close()
    sys.exit(0)

print(f"Found {len(rows)} state restore statements")

# -------------------------------------------------
# Execute restore SQL
# -------------------------------------------------
for table_name, restore_sql in rows:
    print("\n----------------------------------------")
    print(f"Restoring state for table: {table_name}")
    print("Restore SQL:")
    print(restore_sql)

    try:
        cursor.execute(restore_sql)
        print("State restored successfully")

        cursor.execute(f"""
            INSERT INTO ddl_audit_log VALUES (
                current_timestamp(),
                '{REVERT_COMMIT}',
                '{restore_sql.replace("'", "''")}',
                'STATE_ROLLBACK',
                'SUCCESS'
            )
        """)

    except Exception as e:
        cursor.execute(f"""
            INSERT INTO ddl_audit_log VALUES (
                current_timestamp(),
                '{REVERT_COMMIT}',
                '{restore_sql.replace("'", "''")}',
                'STATE_ROLLBACK',
                'FAILED'
            )
        """)

        raise Exception(
            f"Failed to restore state for table {table_name}: {str(e)}"
        )

# -------------------------------------------------
# Cleanup
# -------------------------------------------------
cursor.close()
conn.close()

print("\nSTATE rollback completed successfully")