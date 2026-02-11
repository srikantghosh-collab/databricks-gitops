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

# 3️⃣ Load DDL artifact
import json

with open("ddl_output.json") as f:
    data = json.load(f)

ddls = data.get("ddls", [])

if not ddls:
    print("No DDL to execute")
    cursor.close()
    conn.close()
    exit(0)

# 4️⃣ Execute each DDL
for item in ddls:

    ddl_sql = item["stmt"]
    ddl_type = item["type"]

    print("\nProcessing:", ddl_sql)

    if ddl_type == "DROP":
        print("DROP detected. Taking backup...")

        table_name = ddl_sql.split()[-1].replace(";", "")

        subprocess.check_call(
            ["python", "scripts/backup_before_drop.py"],
            env={
                **os.environ,
                "DDL_TABLE_NAME": table_name
            }
        )

    print("Executing:")
    print(ddl_sql)

    cursor.execute(ddl_sql)
    print("Executed successfully")





