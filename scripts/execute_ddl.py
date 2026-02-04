from databricks import sql
import os

# Path to DDL file
DDL_FILE = "ddl/orders.sql"

print("Starting DDL execution...")

# 1️⃣ Connect to Databricks SQL Warehouse
conn = sql.connect(
    server_hostname=os.environ["DATABRICKS_HOST"],
    http_path=os.environ["DATABRICKS_HTTP_PATH"],
    access_token=os.environ["DATABRICKS_TOKEN"]
)

cursor = conn.cursor()

# 2️⃣ IMPORTANT: Set correct catalog & schema
cursor.execute("USE CATALOG hive_metastore")
cursor.execute("USE SCHEMA default")
print("Catalog & schema set")

# 3️⃣ Read DDL from file
with open(DDL_FILE, "r") as f:
    ddl_sql = f.read().strip()

print("Executing DDL:")
print(ddl_sql)

# 4️⃣ Execute DDL
cursor.execute(ddl_sql)
print("DDL executed successfully")

# 5️⃣ Cleanup
cursor.close()
conn.close()
print("Connection closed")



