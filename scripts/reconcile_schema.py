from databricks import sql
import os
import yaml
import sys

print("Starting schema reconciliation...")

# --------------------------------------------------
# CONFIG
# --------------------------------------------------
CATALOG = "hive_metastore"
SCHEMA = "default"

AUTO_FIX = os.environ.get("AUTO_FIX", "false").lower() == "true"
SCHEMA_FILE = "schemas/tables.yaml"

print(f"AUTO_FIX mode: {AUTO_FIX}")

# --------------------------------------------------
# Connect to Databricks
# --------------------------------------------------
conn = sql.connect(
    server_hostname=os.environ["DATABRICKS_HOST"],
    http_path=os.environ["DATABRICKS_HTTP_PATH"],
    access_token=os.environ["DATABRICKS_TOKEN"]
)

cursor = conn.cursor()
cursor.execute(f"USE CATALOG {CATALOG}")
cursor.execute(f"USE SCHEMA {SCHEMA}")

# --------------------------------------------------
# Load desired schema (Git)
# --------------------------------------------------
if not os.path.exists(SCHEMA_FILE):
    raise Exception(f"{SCHEMA_FILE} not found")

with open(SCHEMA_FILE) as f:
    desired_config = yaml.safe_load(f)

desired_tables = {
    t["name"]: t
    for t in desired_config.get("tables", [])
}

print("Desired tables:", set(desired_tables.keys()))

# --------------------------------------------------
# Fetch live tables
# --------------------------------------------------
cursor.execute("SHOW TABLES")
rows = cursor.fetchall()
live_tables = {row[1] for row in rows}

print("Live tables:", live_tables)

# --------------------------------------------------
# Drift detection
# --------------------------------------------------
missing_tables = set(desired_tables.keys()) - live_tables
extra_tables = live_tables - set(desired_tables.keys())

drift_found = False

# --------------------------------------------------
# Missing tables
# --------------------------------------------------
for table_name in missing_tables:
    drift_found = True
    print(f"❌ DRIFT: Missing table detected: {table_name}")

    if AUTO_FIX:
        table_def = desired_tables[table_name]
        cols = ", ".join(
            f"{c['name']} {c['type']}"
            for c in table_def.get("columns", [])
        )
        create_sql = f"CREATE TABLE {table_name} ({cols})"
        try:
            cursor.execute(create_sql)
            print(f"Auto-created table: {table_name}")
        except Exception as e:
            print(f"Auto-create failed for {table_name}: {e}")
            sys.exit(1)

# --------------------------------------------------
# Extra tables (never auto-delete)
# --------------------------------------------------
PROTECTED_TABLES = {"ddl_audit_log"}

for table_name in extra_tables:
    if table_name in PROTECTED_TABLES or "__backup__" in table_name:
        continue

    drift_found = True
    print(f"❌ DRIFT: Extra table detected: {table_name}")

# --------------------------------------------------
# Property reconciliation
# --------------------------------------------------
for table_name, table_def in desired_tables.items():

    if table_name not in live_tables:
        continue

    expected_props = table_def.get("properties", {})

    if not expected_props:
        continue

    cursor.execute(f"DESCRIBE DETAIL {table_name}")
    detail = cursor.fetchone()

    actual_props = detail.asDict().get("properties", {})

    for key, expected_val in expected_props.items():
        actual_val = actual_props.get(key)

        if actual_val != expected_val:
            drift_found = True
            print(
                f"❌ DRIFT: Property mismatch on {table_name} "
                f"[{key}] expected={expected_val}, actual={actual_val}"
            )

# --------------------------------------------------
# Final decision
# --------------------------------------------------
cursor.close()
conn.close()

if drift_found:
    print("Schema drift detected. Failing pipeline.")
    sys.exit(1)

print("Schema reconciliation successful. No drift detected.")