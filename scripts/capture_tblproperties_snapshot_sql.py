from databricks import sql
from azure.storage.blob import BlobClient
import os
import sys
from datetime import datetime

TABLE_NAME = os.environ.get("TABLE_NAME")
COMMIT_ID = os.environ.get("COMMIT_ID")

if not TABLE_NAME or not COMMIT_ID:
    print("ERROR: TABLE_NAME or COMMIT_ID not provided")
    sys.exit(1)

print(f"Capturing TBLPROPERTIES snapshot for {TABLE_NAME}")

# ----------------------------
# Connect to Databricks
# ----------------------------
conn = sql.connect(
    server_hostname=os.environ["DATABRICKS_HOST"],
    http_path=os.environ["DATABRICKS_HTTP_PATH"],
    access_token=os.environ["DATABRICKS_TOKEN"],
)

cursor = conn.cursor()
cursor.execute(f"DESCRIBE DETAIL {TABLE_NAME}")
row = cursor.fetchone()
props = row.asDict().get("properties", {})

cursor.close()
conn.close()

# ----------------------------
# Generate rollback SQL
# ----------------------------
lines = [
    f"-- Rollback snapshot for table: {TABLE_NAME}",
    f"-- Commit: {COMMIT_ID}",
    f"-- Captured at: {datetime.utcnow().isoformat()}Z",
    "",
    f"ALTER TABLE {TABLE_NAME}",
    "SET TBLPROPERTIES ("
]

prop_lines = [f"  '{k}' = '{v}'" for k, v in props.items()]
lines.append(",\n".join(prop_lines))
lines.append(");")

rollback_sql = "\n".join(lines)

# ----------------------------
# Upload to Blob Storage
# ----------------------------
blob_path = f"tblproperties/{TABLE_NAME}/{COMMIT_ID}.sql"

blob = BlobClient(
    account_url=os.environ["AZURE_BLOB_ACCOUNT_URL"],
    container_name="rollback-sql",
    blob_name=blob_path,
    credential=os.environ["AZURE_BLOB_SAS"]
)

blob.upload_blob(rollback_sql, overwrite=True)

print(f"Rollback SQL uploaded to Blob: rollback-sql/{blob_path}")
