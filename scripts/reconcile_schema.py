from databricks import sql
import os
import yaml
import json

print(" Starting schema reconciliation...")

# CONFIG

CATALOG = "hive_metastore"
SCHEMA = "default"

# AUTO_FIX toggle (default = false for safety)
AUTO_FIX = os.environ.get("AUTO_FIX", "false").lower() == "true"

SCHEMA_FILE = "schemas/tables.yaml"

print(f"AUTO_FIX mode: {AUTO_FIX}")
 
# Connect to Databricks

conn = sql.connect(
    server_hostname=os.environ["DATABRICKS_HOST"],
    http_path=os.environ["DATABRICKS_HTTP_PATH"],
    access_token=os.environ["DATABRICKS_TOKEN"]
)

cursor = conn.cursor()

cursor.execute(f"USE CATALOG {CATALOG}")
cursor.execute(f"USE SCHEMA {SCHEMA}")

# Load desired schema (Git)

if not os.path.exists(SCHEMA_FILE):
    raise Exception(f"{SCHEMA_FILE} not found")

with open(SCHEMA_FILE) as f:
    desired_config = yaml.safe_load(f)

desired_tables = {
    t["name"]
    for t in desired_config.get("tables", [])
}

    
print("Desired tables:", desired_tables)

# Get live tables (Databricks)

cursor.execute("SHOW TABLES")
rows = cursor.fetchall()

live_tables = {row[1] for row in rows}

print("Live tables:", live_tables)

# Drift detection

missing = desired_tables - live_tables
extra = live_tables - desired_tables

print("Missing tables:", missing)
print("Extra tables:", extra)


# Helper: Audit logging

def log_audit(action, sql_stmt, status):

    audit_sql = f"""
    INSERT INTO ddl_audit_log VALUES (
        current_timestamp(),
        'reconciliation',
        '{sql_stmt.replace("'", "''")}',
        '{action}',
        '{status}'
    )
    """

    cursor.execute(audit_sql)
    
# Helper: Build CREATE TABLE SQL

def build_create_sql(table_def):

    cols = []

    for col in table_def["columns"]:
        cols.append(f"{col['name']} {col['type']}")

    columns_sql = ", ".join(cols)

    return f"CREATE TABLE {table_def['name']} ({columns_sql})"

# Auto-fix: Create missing tables

table_map = {
    t["name"]: t
    for t in desired_config.get("tables", [])
}

for table_name in missing:

    table_def = table_map[table_name]
    create_sql = build_create_sql(table_def)


    if AUTO_FIX:
        try:
            print(f"Creating missing table: {table_name}")
            cursor.execute(create_sql)
            log_audit("AUTO_CREATE", create_sql, "SUCCESS")

        except Exception as e:
            print(f"Failed to create {table_name}:", str(e))
            log_audit("AUTO_CREATE", create_sql, "FAILED")

    else:
        print(f"⚠ Missing table detected (manual review): {table_name}")

        


# Detect Extra Tables (Manual Review Only)


PROTECTED_TABLES = {"ddl_audit_log"}

for table_name in extra:

    # Skip protected & backup tables
    if table_name in PROTECTED_TABLES or "_backup_" in table_name:
        print(f"Skipping protected table: {table_name}")
        continue

    print(f"⚠ Extra table detected (manual review required): {table_name}")

    drop_sql = f"DROP TABLE IF EXISTS {table_name}"

    # Log drift only (NO DELETE)
    log_audit("DRIFT_EXTRA_TABLE", drop_sql, "REVIEW_REQUIRED")


# Cleanup


cursor.close()
conn.close()

print(" Reconciliation complete")
