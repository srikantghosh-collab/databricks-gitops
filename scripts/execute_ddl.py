import os
import sys
from databricks import sql

BASE_DIR = os.environ.get("BUILD_SOURCESDIRECTORY", os.getcwd())
DDL_FILE = os.path.join(BASE_DIR, "ddl", "orders.sql")

print(f"Using DDL file: {DDL_FILE}")

if not os.path.exists(DDL_FILE):
    print("DDL file not found")
    sys.exit(1)

with open(DDL_FILE, "r") as f:
    ddl = f.read().strip()

if not ddl:
    print("DDL file is empty")
    sys.exit(1)

print("===================================")
print("Executing DDL:")
print(ddl)
print("===================================")

conn = sql.connect(
    server_hostname=os.environ["DATABRICKS_HOST"].replace("https://", ""),
    http_path=os.environ["DATABRICKS_HTTP_PATH"],
    access_token=os.environ["DATABRICKS_TOKEN"]
)

cursor = conn.cursor()
cursor.execute(ddl)
cursor.close()
conn.close()

print("DDL executed successfully")



