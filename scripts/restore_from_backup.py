import json
import os
from databricks import sql

with open("rollback_metadata.json") as f:
    meta = json.load(f)

original = meta["original_table"]
backup = meta["backup_table"]

restore_sql = f"""
DROP TABLE IF EXISTS {original};

CREATE TABLE {original}
AS SELECT * FROM {backup};
"""

print("Executing restore:")
print(restore_sql)

conn = sql.connect(
    server_hostname=os.environ["DATABRICKS_HOST"],
    http_path=os.environ["DATABRICKS_HTTP_PATH"],
    access_token=os.environ["DATABRICKS_TOKEN"],
)

cursor = conn.cursor()
cursor.execute(f"DROP TABLE IF EXISTS {original}")
cursor.execute(f"""
CREATE TABLE {original}
AS SELECT * FROM {backup}
""")


print("Restore complete ✅")
