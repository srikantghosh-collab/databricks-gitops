import os
from databricks import sql

DDL_FILE = "ddl/orders.sql"

with open(DDL_FILE, "r") as f:
    ddl = f.read().strip()

if not ddl:
    raise Exception("DDL file is empty")

print("===================================")
print("Executing DDL from orders.sql:")
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


