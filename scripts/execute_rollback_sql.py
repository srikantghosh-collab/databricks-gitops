from databricks import sql
from azure.storage.blob import BlobClient
import os
import sys

TABLE_NAME = os.environ.get("TABLE_NAME")
COMMIT_ID = os.environ.get("REVERT_COMMIT")

if not TABLE_NAME or not COMMIT_ID:
    print("ERROR: TABLE_NAME or REVERT_COMMIT not provided")
    sys.exit(1)

blob_path = f"tblproperties/{TABLE_NAME}/{COMMIT_ID}.sql"

print(f"Fetching rollback SQL from Blob: {blob_path}")

blob = BlobClient(
    account_url=os.environ["AZURE_BLOB_ACCOUNT_URL"],
    container_name="rollback-sql",
    blob_name=blob_path,
    credential=os.environ["AZURE_BLOB_SAS"]
)

rollback_sql = blob.download_blob().readall().decode("utf-8")

print("\nExecuting rollback SQL:\n")
print(rollback_sql)

conn = sql.connect(
    server_hostname=os.environ["DATABRICKS_HOST"],
    http_path=os.environ["DATABRICKS_HTTP_PATH"],
    access_token=os.environ["DATABRICKS_TOKEN"],
)

cursor = conn.cursor()
cursor.execute(rollback_sql)

cursor.close()
conn.close()

print("Rollback SQL executed successfully")
