import yaml
import os
from databricks import sql

print("🔵 Starting schema reconciliation...")

# Load desired schema from Git
with open("schemas/tables.yaml") as f:
    desired = yaml.safe_load(f)

desired_tables = {t["name"]: t for t in desired["tables"]}

# Connect to Databricks
conn = sql.connect(
    server_hostname=os.environ["DATABRICKS_HOST"],
    http_path=os.environ["DATABRICKS_HTTP_PATH"],
    access_token=os.environ["DATABRICKS_TOKEN"],
)

cursor = conn.cursor()

# Fetch live tables
cursor.execute("SHOW TABLES IN default")
live_tables = {row[1] for row in cursor.fetchall()}

print("Live tables:", live_tables)
print("Desired tables:", set(desired_tables.keys()))

missing_tables = set(desired_tables.keys()) - live_tables
extra_tables = live_tables - set(desired_tables.keys())

print("Missing tables:", missing_tables)
print("Extra tables:", extra_tables)

# Function to generate CREATE TABLE
def generate_create(table):
    cols = ", ".join(
        f'{c["name"]} {c["type"]}'
        for c in table["columns"]
    )
    return f"CREATE TABLE {table['name']} ({cols})"

# Create missing tables
for name in missing_tables:
    table = desired_tables[name]
    ddl = generate_create(table)
    print("Executing:", ddl)
    cursor.execute(ddl)

# Warn about extra tables (do NOT auto-drop)
for table in extra_tables:
    print(f"⚠️ Extra table detected (manual review needed): {table}")

print("✅ Reconciliation complete")
