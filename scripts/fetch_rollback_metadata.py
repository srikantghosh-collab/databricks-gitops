import json
import os
from azure.storage.blob import BlobServiceClient

ACCOUNT_URL = os.environ["AZURE_BLOB_ACCOUNT_URL"]
SAS_TOKEN = os.environ["AZURE_BLOB_SAS"]
CONTAINER = "rollback-metadata"

table = os.environ["TABLE_NAME"]
commit = os.environ["REVERT_COMMIT"]

blob_path = f"{table}/{commit}.json"

client = BlobServiceClient(
    account_url=ACCOUNT_URL,
    credential=SAS_TOKEN
)

blob = client.get_blob_client(container=CONTAINER, blob=blob_path)

data = blob.download_blob().readall()

with open("rollback_metadata.json", "wb") as f:
    f.write(data)

print("Rollback metadata downloaded successfully")
