from databricks import sql
import os
import json
import re
import sys
import subprocess

print("Starting DDL execution...")

DDL_ARTIFACT = "ddl_output.json"

# -------------------------------------------------
# Load DDL artifact
# -------------------------------------------------
if not os.path.exists(DDL_ARTIFACT):
    print("DDL artifact not found — skipping execution")
    sys.exit(0)

with open(DDL_ARTIFACT) as f:
    payload = json.load(f)

ddls = payload.get("ddls", [])
if not ddls:
    print("No DDL statements to execute — exiting")
    sys.exit(0)

commit_id = payload.get("commit_id") or subprocess.check_output(
    ["git", "rev-parse", "HEAD"], text=True
).strip()

rollback_type = os.environ.get("ROLLBACK_TYPE", "NONE")
is_drop = os.environ.get("IS_DROP", "false") == "true"

print(f"Rollback type: {rollback_type}")
print(f"Is drop: {is_drop}")

# -------------------------------------------------
# Connect to Databricks
# -------------------------------------------------
conn = sql.connect(
    server_hostname=os.environ["DATABRICKS_HOST"],
    http_path=os.environ["DATABRICKS_HTTP_PATH"],
    access_token=os.environ["DATABRICKS_TOKEN"],
)

cursor = conn.cursor()
cursor.execute("USE CATALOG hive_metastore")
cursor.execute("USE SCHEMA default")
print("Catalog & schema set")

# =================================================
# Helpers
# =================================================
def extract_table_name(ddl_sql):
    patterns = [
        r"CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+([^\s(]+)",
        r"CREATE\s+TABLE\s+([^\s(]+)",
        r"ALTER\s+TABLE\s+([^\s;]+)",
        r"DROP\s+TABLE\s+IF\s+EXISTS\s+([^\s;]+)",
        r"DROP\s+TABLE\s+([^\s;]+)"
    ]
    for p in patterns:
        m = re.search(p, ddl_sql, re.IGNORECASE)
        if m:
            return m.group(1)
    return None

# =================================================
# Decide BACKUP MODE (ONCE PER COMMIT)
# =================================================
ddl_text = " ".join(d["statement"].upper() for d in ddls)

if "DROP TABLE" in ddl_text:
    backup_mode = "DATA_BACKUP"
elif "ALTER TABLE" in ddl_text:
    backup_mode = "STATE_BACKUP"
else:
    backup_mode = "NONE"

print(f"Backup mode selected: {backup_mode}")

# =================================================
# Perform backup BEFORE execution
# =================================================
backed_up_tables = {}

if backup_mode != "NONE":
    # collect DDLs per table so we can provide the specific ddl_sql when doing state backups
    for item in ddls:
        table_name = extract_table_name(item["statement"])
        if table_name:
            ddl_stmt = item["statement"].strip()
            backed_up_tables.setdefault(table_name, []).append(ddl_stmt)

    if backup_mode == "DATA_BACKUP":
        for table in backed_up_tables.keys():
            print(f"DATA_BACKUP → {table}")
            subprocess.check_call(
                ["python", "scripts/backup_before_drop.py"],
                env={**os.environ, "DDL_TABLE_NAME": table, "COMMIT_ID": commit_id},
            )

    elif backup_mode == "STATE_BACKUP":
        for table, ddl_list in backed_up_tables.items():
            for ddl_sql in ddl_list:
                print(f"STATE_BACKUP → {table}")
                subprocess.check_call(
                    ["python", "scripts/capture_table_state.py"],
                    env={**os.environ, "TABLE_NAME": table, "DDL_SQL": ddl_sql, "COMMIT_ID": commit_id},
                )

# =================================================
# Execute DDLs
# =================================================
failed = False
error_msg = None

for item in ddls:
    ddl_sql = item["statement"].strip()
    try:
        print("\nExecuting DDL:")
        print(ddl_sql)
        cursor.execute(ddl_sql)

        cursor.execute(f"""
            INSERT INTO ddl_audit_log VALUES (
                current_timestamp(),
                '{commit_id}',
                '{ddl_sql.replace("'", "''")}',
                'EXECUTE',
                'SUCCESS'
            )
        """)
    except Exception as e:
        failed = True
        error_msg = str(e)
        break

cursor.close()
conn.close()

if failed:
    raise Exception(f"DDL execution stopped due to failure: {error_msg}")

print("\nAll DDL statements executed successfully")