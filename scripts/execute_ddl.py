from databricks import sql
import os
import subprocess

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

# 🔥 ADD THIS BLOCK (EXACT PLACE)
ddl_upper = ddl_sql.upper()

if ddl_upper.startswith("DROP"):
    print("DROP detected. Taking backup before execution...")

    # extract table name (simple logic)
    table_name = ddl_sql.split()[-1].replace(";", "")

    subprocess.check_call(
        ["python", "scripts/backup_before_drop.py"],
        env={
            **os.environ,
            "DDL_TABLE_NAME": table_name
        }
    )

# 4️⃣ Execute DDL
print("Executing DDL:")
print(ddl_sql)

cursor.execute(ddl_sql)
print("DDL executed successfully")

# 5️⃣ Cleanup
cursor.close()
conn.close()
print("Connection closed")




