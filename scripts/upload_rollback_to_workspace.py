import requests
import base64
import os

commit_id = os.environ.get("COMMIT_ID")

ROLLBACK_FILE = os.path.join(
    os.environ.get("SYSTEM_DEFAULTWORKINGDIRECTORY", "."),
    "rollback.sql"
)

with open(ROLLBACK_FILE, "r") as f:
    content = f.read()

encoded_content = base64.b64encode(content.encode()).decode()

url = f"https://{os.environ['DATABRICKS_HOST']}/api/2.0/workspace/import"

payload = {
    "path": f"/Workspace/rollback_scripts/rollback_{commit_id}.sql",
    "format": "SOURCE",
    "language": "SQL",
    "content": encoded_content,
    "overwrite": True
}

headers = {
    "Authorization": f"Bearer {os.environ['DATABRICKS_TOKEN']}"
}

response = requests.post(url, json=payload, headers=headers)

print(response.status_code)
print(response.text)