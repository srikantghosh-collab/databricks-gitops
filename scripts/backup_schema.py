import json, subprocess, os

with open("ddl_output.json") as f:
    ddl = json.load(f)["ddl"]

if "DROP TABLE" not in ddl.upper():
    print("No backup required")
    exit(0)

table = ddl.split()[-1]
os.makedirs("ledger/schema_backup", exist_ok=True)

cmd = f'databricks sql execute --warehouse-id $WAREHOUSE_ID --command "SHOW CREATE TABLE {table}"'
schema = subprocess.check_output(cmd, shell=True, text=True)

with open(f"ledger/schema_backup/{table}.sql", "w") as f:
    f.write(schema)

print("Backup saved")
