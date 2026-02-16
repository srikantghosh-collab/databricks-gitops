import os
import sys
from azure.storage.blob import BlobClient

#  Get reverted commit ID explicitly from pipeline
commit_id = os.getenv("REVERT_COMMIT")

if not commit_id:
    print("ERROR: REVERT_COMMIT environment variable not provided")
    sys.exit(1)

#  Read Azure Blob configuration
account_url = os.getenv("AZURE_BLOB_ACCOUNT_URL")
container_name = os.getenv("AZURE_BLOB_CONTAINER")
sas_token = os.getenv("AZURE_BLOB_SAS")

missing = []
if not account_url:
    missing.append("AZURE_BLOB_ACCOUNT_URL")
if not container_name:
    missing.append("AZURE_BLOB_CONTAINER")
if not sas_token:
    missing.append("AZURE_BLOB_SAS")

if missing:
    print(f"ERROR: Missing environment variables: {', '.join(missing)}")
    sys.exit(1)

#  Create Blob client (metadata stored as <commit_id>.json)
blob_name = f"{commit_id}.json"

print(f"Fetching rollback metadata for commit: {commit_id}")
print(f"Blob: {container_name}/{blob_name}")

blob = BlobClient(
    account_url=account_url,
    container_name=container_name,
    blob_name=blob_name,
    credential=sas_token
)

#  Download metadata
data = blob.download_blob().readall()

with open("rollback_metadata.json", "wb") as f:
    f.write(data)

print("Rollback metadata successfully fetched and saved as rollback_metadata.json")
