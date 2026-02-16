import json
import os
from azure.storage.blob import BlobServiceClient

ACCOUNT_URL = os.environ["AZURE_BLOB_ACCOUNT_URL"]
CONTAINER = "rollback-metadata"
SAS_TOKEN = os.environ["AZURE_BLOB_SAS"]

with open("rollback_metadata.json") as f:
    metadata = json.load(f)

table = metadata["original_table"]
commit = metadata["commit_id"]

blob_path = f"{table}/{commit}.json"

client = BlobServiceClient(
    account_url=ACCOUNT_URL,
    credential=SAS_TOKEN
)

blob = client.get_blob_client(container=CONTAINER, blob=blob_path)
blob.upload_blob(json.dumps(metadata), overwrite=True)

print(f"Rollback metadata uploaded to blob: {blob_path}")
