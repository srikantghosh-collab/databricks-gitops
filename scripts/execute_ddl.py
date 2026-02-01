import os
import subprocess

ddl = open("ddl_output.json").read()
warehouse = os.getenv("Warehouse_ID")

cmd = f'databricks sql execute --warehouse-id {warehouse} --command "{ddl}"'
subprocess.check_call(cmd, shell=True)
