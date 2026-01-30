import json, subprocess

with open("ddl_output.json") as f:
    ddl = json.load(f)["ddl"]

cmd = f'databricks sql execute --warehouse-id $WAREHOUSE_ID --command "{ddl}"'
subprocess.check_call(cmd, shell=True)

print("DDL executed")
