import os
import subprocess
import requests
import base64

print("Starting rollback execution...")

# =================================================
# ENV VARIABLES
# =================================================

DATABRICKS_HOST = os.environ.get("DATABRICKS_HOST")
DATABRICKS_TOKEN = os.environ.get("DATABRICKS_TOKEN")
WAREHOUSE_ID = os.environ.get("WAREHOUSE_ID")
REVERT_COMMIT = os.environ.get("REVERT_COMMIT")

# =================================================
# WORKSPACE PATH (commit-based)
# =================================================

WORKSPACE_PATH = f"/rollback_scripts/rollback_{REVERT_COMMIT}.sql"

LOCAL_FILE = "rollback.sql"

# =================================================
# DOWNLOAD FROM DATABRICKS WORKSPACE
# =================================================

print(f"Fetching rollback script from workspace: {WORKSPACE_PATH}")

url = f"{DATABRICKS_HOST}/api/2.0/workspace/export"

try:
    response = requests.get(
        url,
        headers={"Authorization": f"Bearer {DATABRICKS_TOKEN}"},
        params={
            "path": WORKSPACE_PATH,
            "format": "SOURCE"
        }
    )

    if response.status_code != 200:
        print(f"Rollback file not found in workspace: {WORKSPACE_PATH}")
        exit(1)

    response_json = response.json()

    encoded_content = response_json.get("content")

    if not encoded_content:
     print("No content found in workspace file")
    exit(1)

    decoded_sql = base64.b64decode(encoded_content).decode("utf-8")

    with open(LOCAL_FILE, "w") as f:
       f.write(decoded_sql)

       print("Rollback file downloaded and decoded successfully")

except Exception as e:
    print(f"Failed to fetch rollback from workspace: {e}")
    exit(1)

# =================================================
# VALIDATE FILE
# =================================================

if not os.path.exists(LOCAL_FILE):
    print("rollback.sql not found — nothing to restore")
    exit(0)

# =================================================
# READ SQL
# =================================================

with open(LOCAL_FILE) as f:
    sql_text = f.read()
    sql_text = sql_text.replace("-- COMMAND ----------", "")

# =================================================
# SPLIT STATEMENTS
# =================================================

statements = [
    stmt.strip()
    for stmt in sql_text.split(";")
    if stmt.strip()
]

print(f"Executing {len(statements)} rollback statements")

# =================================================
# EXECUTE
# =================================================

for stmt in statements:
    print(f"Running: {stmt}")

    cmd = f'databricks sql execute --warehouse-id {WAREHOUSE_ID} --command "{stmt}"'

    subprocess.check_call(cmd, shell=True)

print("Rollback executed successfully")