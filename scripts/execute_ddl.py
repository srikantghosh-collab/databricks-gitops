import os
from databricks import sql

base_dir = os.environ.get("BUILD_SOURCESDIRECTORY", os.getcwd())
ddl_file = os.path.join(base_dir, "ddl", "orders.sql")

print("Using DDL file:", ddl_file)

with open(ddl_file) as f:
    ddl_sql = f.read()

conn = sql.connect(
    server_hostname=os.environ["DATABRICKS_HOST"].replace("https://", ""),
    http_path=os.environ["DATABRICKS_HTTP_PATH"],
    access_token=os.environ["DATABRICKS_TOKEN"]
)

cursor = conn.cursor()
cursor.execute(ddl_sql)
cursor.close()
conn.close()

print("DDL executed successfully")





