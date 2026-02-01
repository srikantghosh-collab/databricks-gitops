import os
import json
import subprocess
import sys

if not os.path.exists("ddl_output.json"):
    print("No DDL detected. Skipping execution.")
    sys.exit(0)

with open("ddl_output.json") as f:
    ddl = json.load(f)["ddl"]

warehouse = os.getenv("Warehouse_ID")

cmd = f'databricks sql execute --warehouse-id {warehouse} --command "{ddl}"'
subprocess.check_call(cmd, shell=True)
condition: |
 and(
    succeeded(),
    exists('ddl_output.json')
  )

print("DDL executed successfully")
