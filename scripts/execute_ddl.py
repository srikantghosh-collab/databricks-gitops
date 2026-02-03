import os
from databricks import sql

DDL_FILE = "ddl/orders.sql"

print(f"Using DDL file: {os.path.abspath(DDL_FILE)}")

if not os.path.exists(DDL_FILE):
    raise FileNotFoundError("DDL file not found")

with open(DDL_FILE, "r") as f:
    ddl_sql = f.read()

conn = sql.connect(
    server_hostname=os.environ["DATABRICKS_HOST"].replace("https://", ""),
    http_path=os.environ["DATABRICKS_HTTP_PATH"],
    access_token=os.environ["DATABRICKS_TOKEN"]
)

cursor = conn.cursor()

# 🔥 VERY IMPORTANT
cursor.execute("USE CATALOG hive_metastore")
cursor.execute("USE SCHEMA default")

print("Catalog & schema set")

for stmt in ddl_sql.split(";"):
    stmt = stmt.strip()
    if stmt:
        print(f"Executing: {stmt}")
        cursor.execute(stmt)

cursor.close()
conn.close()

print("DDL executed successfully")

