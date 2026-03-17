import os
import requests
import base64
from databricks import sql

print("Starting rollback execution...")

DATABRICKS_HOST = os.environ["DATABRICKS_HOST"]
DATABRICKS_TOKEN = os.environ["DATABRICKS_TOKEN"]
DATABRICKS_HTTP_PATH = os.environ["DATABRICKS_HTTP_PATH"]
REVERT_COMMIT = os.environ["REVERT_COMMIT"]

WORKSPACE_PATH = f"/rollback_scripts/rollback_{REVERT_COMMIT}.sql"

# ----------------------------------------
# Fetch rollback SQL from workspace
# ----------------------------------------

url = f"{DATABRICKS_HOST}/api/2.0/workspace/export"

print(f"Fetching rollback script from workspace: {WORKSPACE_PATH}")

response = requests.get(
    url,
    headers={"Authorization": f"Bearer {DATABRICKS_TOKEN}"},
    params={"path": WORKSPACE_PATH, "format": "SOURCE"}
)

if response.status_code != 200:
    print("Rollback file not found")
    exit(1)

# ----------------------------------------
# ✅ Decode base64 content
# ----------------------------------------

data = response.json()

encoded = data.get("content")

if not encoded:
    print("Empty rollback content")
    exit(1)

sql_text = base64.b64decode(encoded).decode("utf-8")

print("Rollback file downloaded and decoded successfully")

# ----------------------------------------
# Clean notebook format
# ----------------------------------------

sql_text = sql_text.replace("-- COMMAND ----------", "")

# ----------------------------------------
# Split statements
# ----------------------------------------

statements = [
    s.strip()
    for s in sql_text.split(";")
    if s.strip()
]

print(f"Executing {len(statements)} rollback statements")

# ----------------------------------------
# Connect to Databricks
# ----------------------------------------

conn = sql.connect(
    server_hostname=DATABRICKS_HOST.replace("https://", ""),
    http_path=DATABRICKS_HTTP_PATH,
    access_token=DATABRICKS_TOKEN
)

cursor = conn.cursor()

# ----------------------------------------
# Execute statements
# ----------------------------------------

for stmt in statements:
    print(f"Running: {stmt}")
    cursor.execute(stmt)

print("Rollback executed successfully")

cursor.close()
conn.close()