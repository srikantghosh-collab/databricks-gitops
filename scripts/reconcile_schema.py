from databricks import sql
import os
import yaml

print("Starting schema reconciliation...", flush=True)

# CONFIG

CATALOG = "hive_metastore"
AUTO_FIX = os.environ.get("AUTO_FIX", "false").lower() == "true"

SCHEMA_FILE = "schemas/tables.yaml"

print(f"AUTO_FIX mode: {AUTO_FIX}", flush=True)

# Connect to Databricks

conn = sql.connect(
    server_hostname=os.environ["DATABRICKS_HOST"],
    http_path=os.environ["DATABRICKS_HTTP_PATH"],
    auth_type="azure-client-secret",
    azure_client_id=os.environ["DATABRICKS_CLIENT_ID"],
    azure_client_secret=os.environ["CLIENT_SECRET"],
    azure_tenant_id=os.environ["TENANT_ID"],
)

cursor = conn.cursor()

cursor.execute(f"USE CATALOG {CATALOG}")

# Load desired schema (Git)

if not os.path.exists(SCHEMA_FILE):
    raise Exception(f"{SCHEMA_FILE} not found")

with open(SCHEMA_FILE) as f:
    desired_config = yaml.safe_load(f)

desired_tables = {
    t["name"]
    for t in desired_config.get("tables", [])
}

print("Desired tables:", desired_tables, flush=True)

# --------------------------------------
# Detect live tables across ALL schemas
# --------------------------------------

print("Fetching schemas...", flush=True)

cursor.execute("SHOW DATABASES")
schemas = [row[0] for row in cursor.fetchall()]

print(f"Found {len(schemas)} schemas", flush=True)

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

# --------------------------------------
# Drift detection
# --------------------------------------

missing = desired_tables - live_table_names
extra = live_table_names - desired_tables

print("Missing tables:", missing, flush=True)
print("Extra tables:", extra, flush=True)

# --------------------------------------
# Helper: Audit logging
# --------------------------------------

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

# --------------------------------------
# Helper: Build CREATE TABLE SQL
# --------------------------------------

def build_create_sql(table_def):

    cols = []

    for col in table_def["columns"]:
        cols.append(f"{col['name']} {col['type']}")

    columns_sql = ", ".join(cols)

    schema = table_def.get("schema", "default")

    return f"CREATE TABLE {schema}.{table_def['name']} ({columns_sql}) USING DELTA"

# --------------------------------------
# Auto-fix: Create missing tables
# --------------------------------------

table_map = {
    t["name"]: t
    for t in desired_config.get("tables", [])
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

# --------------------------------------
# Detect Extra Tables
# --------------------------------------

PROTECTED_TABLES = {"ddl_audit_log"}

for table_name in extra:

    if table_name in PROTECTED_TABLES:
        print(f"Skipping protected table: {table_name}", flush=True)
        continue

    schema = live_tables[table_name]

    print(f"⚠ Extra table detected: {schema}.{table_name}", flush=True)

    drop_sql = f"DROP TABLE IF EXISTS {schema}.{table_name}"

    log_audit("DRIFT_EXTRA_TABLE", drop_sql, "REVIEW_REQUIRED")

# --------------------------------------
# Cleanup
# --------------------------------------

cursor.close()
conn.close()

print("Reconciliation complete", flush=True)