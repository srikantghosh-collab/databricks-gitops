from databricks import sql
import os
import yaml

print("Starting schema reconciliation...", flush=True)

# ------------------------------------------------
# CONFIG
# ------------------------------------------------

CATALOG = "hive_metastore"
AUTO_FIX = os.environ.get("AUTO_FIX", "false").lower() == "true"

SCHEMA_FILE = "schemas/tables.yaml"

print(f"AUTO_FIX mode: {AUTO_FIX}", flush=True)

# ------------------------------------------------
# Connect to Databricks
# ------------------------------------------------

print("Connecting to Databricks...", flush=True)

conn = sql.connect(
    server_hostname=os.environ["DATABRICKS_HOST"],
    http_path=os.environ["DATABRICKS_HTTP_PATH"],
    access_token=os.environ["DATABRICKS_TOKEN"]
)

print("Connection established", flush=True)

cursor = conn.cursor()
print("Cursor created", flush=True)

# ------------------------------------------------
# Load desired schema (Git)
# ------------------------------------------------

if not os.path.exists(SCHEMA_FILE):
    raise Exception(f"{SCHEMA_FILE} not found")

with open(SCHEMA_FILE) as f:
    desired_config = yaml.safe_load(f)

tables_config = desired_config.get("tables", [])

desired_tables = {
    t["name"]
    for t in tables_config
}

print("Desired tables:", desired_tables, flush=True)

# ------------------------------------------------
# Detect schemas from Git config
# ------------------------------------------------

schemas = {
    t.get("schema", "default")
    for t in tables_config
}

print("Schemas detected from Git:", schemas, flush=True)

# ------------------------------------------------
# Fetch live tables
# ------------------------------------------------

live_tables = {}

for schema_name in schemas:

    print(f"Scanning schema: {schema_name}", flush=True)

    try:

        cursor.execute(f"SHOW TABLES IN {schema_name}")
        rows = cursor.fetchall()

        for row in rows:
            table = row[1]
            live_tables[table] = schema_name

    except Exception as e:

        print(f"Skipping schema {schema_name}: {e}", flush=True)

print("Live tables with schema:", live_tables, flush=True)

live_table_names = set(live_tables.keys())

# ------------------------------------------------
# Drift detection
# ------------------------------------------------

missing = desired_tables - live_table_names
extra = live_table_names - desired_tables

print("Missing tables:", missing, flush=True)
print("Extra tables:", extra, flush=True)

# ------------------------------------------------
# Helper: Audit logging
# ------------------------------------------------

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

# ------------------------------------------------
# Helper: Build CREATE TABLE SQL
# ------------------------------------------------

def build_create_sql(table_def):

    cols = []

    for col in table_def["columns"]:
        cols.append(f"{col['name']} {col['type']}")

    columns_sql = ", ".join(cols)

    schema = table_def.get("schema", "default")

    return f"CREATE TABLE {schema}.{table_def['name']} ({columns_sql}) USING DELTA"

# ------------------------------------------------
# Auto-fix: Create missing tables
# ------------------------------------------------

table_map = {
    t["name"]: t
    for t in tables_config
}

for table_name in missing:

    table_def = table_map[table_name]

    create_sql = build_create_sql(table_def)

    if AUTO_FIX:

        try:

            print(f"Creating missing table: {create_sql}", flush=True)

            cursor.execute(create_sql)

            log_audit("AUTO_CREATE", create_sql, "SUCCESS")

        except Exception as e:

            print(f"Failed to create {table_name}: {str(e)}", flush=True)

            log_audit("AUTO_CREATE", create_sql, "FAILED")

    else:

        print(f"⚠ Missing table detected (manual review): {table_name}", flush=True)

# ------------------------------------------------
# Detect Extra Tables
# ------------------------------------------------

PROTECTED_TABLES = {"ddl_audit_log"}

for table_name in extra:

    if table_name in PROTECTED_TABLES:
        print(f"Skipping protected table: {table_name}", flush=True)
        continue

    schema = live_tables[table_name]

    print(f"⚠ Extra table detected: {schema}.{table_name}", flush=True)

    drop_sql = f"DROP TABLE IF EXISTS {schema}.{table_name}"

    log_audit("DRIFT_EXTRA_TABLE", drop_sql, "REVIEW_REQUIRED")

# ------------------------------------------------
# Cleanup
# ------------------------------------------------

cursor.close()
conn.close()

print("Reconciliation complete", flush=True)