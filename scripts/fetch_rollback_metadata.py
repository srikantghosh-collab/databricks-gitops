import os
import subprocess
from azure.storage.blob import BlobClient

commit_id = subprocess.check_output(
    ["git", "rev-parse", "HEAD~1"], text=True
).strip()

blob = BlobClient(
    account_url=os.environ["AZURE_BLOB_ACCOUNT_URL"],
    container_name=os.environ["AZURE_BLOB_CONTAINER"],
    blob_name=f"{commit_id}.json",
    credential=os.environ["AZURE_BLOB_SAS"]
)

data = blob.download_blob().readall()

with open("rollback_metadata.json", "wb") as f:
    f.write(data)

print(f"Rollback metadata fetched for commit {commit_id}")
