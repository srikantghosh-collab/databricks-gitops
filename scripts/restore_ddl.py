import os, subprocess

backup = os.listdir("ledger/schema_backup")[0]
with open(f"ledger/schema_backup/{backup}") as f:
    sql = f.read()

cmd = f'databricks sql execute --warehouse-id $WAREHOUSE_ID --command "{sql}"'
subprocess.check_call(cmd, shell=True)

print("Table restored")
