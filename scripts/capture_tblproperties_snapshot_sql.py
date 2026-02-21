from databricks import sql
import os
import sys
from datetime import datetime

# ----------------------------
# Inputs (from env)
# ----------------------------
TABLE_NAME = os.environ.get("DDL_TABLE_NAME")
COMMIT_ID = os.environ.get("COMMIT_ID")

if not TABLE_NAME or not COMMIT_ID:
    print("ERROR: DDL_TABLE_NAME or COMMIT_ID not provided")
    sys.exit(1)

OUTPUT_DIR = f"rollback/tblproperties/{TABLE_NAME}"
os.makedirs(OUTPUT_DIR, exist_ok=True)

OUTPUT_FILE = f"{OUTPUT_DIR}/{COMMIT_ID}.sql"

print(f"Capturing TBLPROPERTIES snapshot for table: {TABLE_NAME}")

# ----------------------------
# Connect to Databricks
# ----------------------------
conn = sql.connect(
    server_hostname=os.environ["DATABRICKS_HOST"],
    http_path=os.environ["DATABRICKS_HTTP_PATH"],
    access_token=os.environ["DATABRICKS_TOKEN"],
)

cursor = conn.cursor()

# ----------------------------
# Fetch table properties
# ----------------------------
cursor.execute(f"DESCRIBE DETAIL {TABLE_NAME}")
row = cursor.fetchone()

# Databricks returns a MAP in `properties`
properties = row.asDict().get("properties", {})

cursor.close()
conn.close()

# ----------------------------
# Generate rollback SQL
# ----------------------------
sql_lines = []
sql_lines.append(f"-- Rollback snapshot for table: {TABLE_NAME}")
sql_lines.append(f"-- Captured at: {datetime.utcnow().isoformat()}Z")
sql_lines.append(f"-- Commit: {COMMIT_ID}")
sql_lines.append("")

if not properties:
    # First-time SET case → UNSET
    sql_lines.append(
        f"-- No existing properties found, rollback will UNSET modified properties"
    )
else:
    sql_lines.append(f"ALTER TABLE {TABLE_NAME}")
    sql_lines.append("SET TBLPROPERTIES (")

    prop_lines = []
    for k, v in properties.items():
        prop_lines.append(f"  '{k}' = '{v}'")

    sql_lines.append(",\n".join(prop_lines))
    sql_lines.append(");")

rollback_sql = "\n".join(sql_lines)

# ----------------------------
# Write SQL snapshot
# ----------------------------
with open(OUTPUT_FILE, "w") as f:
    f.write(rollback_sql)

print(f"Snapshot rollback SQL generated at: {OUTPUT_FILE}")
print("\n--- Rollback SQL ---")
print(rollback_sql)
