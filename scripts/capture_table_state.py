from databricks import sql
import os
import sys
import subprocess
import re

print("Starting STATE_BACKUP capture...")

# =================================================
# Inputs
# =================================================
DDL_SQL = os.environ.get("DDL_SQL")
TABLE_NAME = os.environ.get("TABLE_NAME")
COMMIT_ID = os.environ.get("COMMIT_ID")

# -------------------------------------------------
# HARD GUARDS (NO FAILURE SCENARIOS)
# -------------------------------------------------

# 1️⃣ DDL not provided → skip safely
if not DDL_SQL or not TABLE_NAME:
    print("DDL_SQL or TABLE_NAME not provided → skipping STATE_BACKUP")
    sys.exit(0)

DDL_UPPER = DDL_SQL.upper()

# 2️⃣ Only ALTER TABLE needs STATE_BACKUP
if not DDL_UPPER.startswith("ALTER TABLE"):
    print("DDL is not ALTER TABLE → STATE_BACKUP not required")
    sys.exit(0)

# 3️⃣ Resolve commit id safely
if not COMMIT_ID:
    COMMIT_ID = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], text=True
    ).strip()

# =================================================
# Databricks connection
# =================================================
conn = sql.connect(
    server_hostname=os.environ["DATABRICKS_HOST"],
    http_path=os.environ["DATABRICKS_HTTP_PATH"],
    access_token=os.environ["DATABRICKS_TOKEN"],
)

cursor = conn.cursor()
cursor.execute("USE CATALOG hive_metastore")
cursor.execute("USE SCHEMA default")

# =================================================
# Helpers
# =================================================
def table_exists(cursor, table):
    try:
        cursor.execute(f"DESCRIBE TABLE {table}")
        return True
    except Exception:
        return False


def get_tblproperties(table):
    cursor.execute(f"SHOW TBLPROPERTIES {table}")
    rows = cursor.fetchall()
    return {r[0]: r[1] for r in rows}


def get_columns(table):
    cursor.execute(f"DESCRIBE TABLE {table}")
    rows = cursor.fetchall()
    cols = {}
    for r in rows:
        if r[0] and not r[0].startswith("#"):
            cols[r[0]] = r[1]
    return cols


# =================================================
# Table existence guard (CRITICAL FIX)
# =================================================
if not table_exists(cursor, TABLE_NAME):
    print(f"Table {TABLE_NAME} does not exist → skipping STATE_BACKUP")
    cursor.close()
    conn.close()
    sys.exit(0)

# =================================================
# Build rollback SQL (STATE BACKUP)
# =================================================
rollback_sql = None

# ----------------- SET TBLPROPERTIES -----------------
if "SET TBLPROPERTIES" in DDL_UPPER:
    current_props = get_tblproperties(TABLE_NAME)

    keys = re.findall(r"'([^']+)'\s*=", DDL_SQL)
    restore_pairs = []

    for k in keys:
        if k in current_props:
            restore_pairs.append(f"'{k}' = '{current_props[k]}'")

    if restore_pairs:
        rollback_sql = (
            f"ALTER TABLE {TABLE_NAME} SET TBLPROPERTIES (\n  "
            + ",\n  ".join(restore_pairs)
            + "\n)"
        )

# ----------------- ADD COLUMN -----------------
elif "ADD COLUMN" in DDL_UPPER:
    col = re.findall(r"ADD COLUMN\s+([^\s]+)", DDL_SQL, re.IGNORECASE)
    if col:
        rollback_sql = f"ALTER TABLE {TABLE_NAME} DROP COLUMN {col[0]}"

# ----------------- CHANGE COLUMN -----------------
elif "CHANGE COLUMN" in DDL_UPPER:
    cols = get_columns(TABLE_NAME)
    col = re.findall(r"CHANGE COLUMN\s+([^\s]+)", DDL_SQL, re.IGNORECASE)
    if col and col[0] in cols:
        rollback_sql = (
            f"ALTER TABLE {TABLE_NAME} CHANGE COLUMN "
            f"{col[0]} {col[0]} {cols[col[0]]}"
        )

# =================================================
# Store STATE_BACKUP
# =================================================
if rollback_sql:
    print("Captured rollback SQL:")
    print(rollback_sql)

    cursor.execute(f"""
        INSERT INTO ddl_state_backup VALUES (
            current_timestamp(),
            '{COMMIT_ID}',
            '{TABLE_NAME}',
            'STATE_BACKUP',
            '{rollback_sql.replace("'", "''")}'
        )
    """)

    print("STATE_BACKUP stored successfully")

else:
    print("No STATE_BACKUP required for this DDL")

# =================================================
# Cleanup
# =================================================
cursor.close()
conn.close()

print("STATE_BACKUP capture completed")