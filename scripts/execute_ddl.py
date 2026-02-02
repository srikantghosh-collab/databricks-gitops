import os
import sys
from databricks import sql

DDL_FILE = os.path.join(
    os.getenv("BUILD_SOURCESDIRECTORY", os.getcwd()),
    "ddl",
    "orders.sql"
)

print(f"Using DDL file: {DDL_FILE}")

if not os.path.exists(DDL_FILE):
    print("DDL file not found")
    sys.exit(1)

with open(DDL_FILE, "r") as f:
    ddl_sql = f.read()

conn = sql.connect(
    server_hostname=os.environ["DATABRICKS_HOST"],
    http_path=os.environ["DATABRICKS_HTTP_PATH"],
    access_token=os.environ["DATABRICKS_TOKEN"]
)

with conn.cursor() as cursor:
    cursor.execute(ddl_sql)

print("DDL executed successfully")




