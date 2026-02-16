import os
from azure.storage.blob import BlobClient

commit_id = os.environ["COMMIT_ID"]

blob = BlobClient(
    account_url=os.environ["AZURE_BLOB_ACCOUNT_URL"],
    container_name=os.environ["AZURE_BLOB_CONTAINER"],
    blob_name=f"{commit_id}.json",
    credential=os.environ["AZURE_BLOB_SAS"]
)

with open("rollback_metadata.json", "rb") as f:
    blob.upload_blob(f, overwrite=True)

print(f"Rollback metadata uploaded for commit {commit_id}")
