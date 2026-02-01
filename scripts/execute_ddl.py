import os
import json
import subprocess
import sys

# Skip execution if no DDL was detected
if not os.path.exists("ddl_output.json"):
    print("No DDL detected. Skipping execution.")
    sys.exit(0)

with open("ddl_output.json") as f:
    ddl = json.load(f)["ddl"]

warehouse_id = os.getenv("Warehouse_ID")

if not warehouse_id:
    print("Warehouse_ID not set")
    sys.exit(1)

cmd = f'databricks sql execute --warehouse-id {warehouse_id} --command "{ddl}"'
print("Executing:", cmd)

subprocess.check_call(cmd, shell=True)

print("DDL executed successfully")

