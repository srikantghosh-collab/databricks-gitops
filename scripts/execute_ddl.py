from databricks import sql
import os
import json
import re
import sys
import subprocess

print("Starting DDL execution...")

# =================================================
# Revert Guard
# =================================================
is_revert = os.environ.get("PIPELINE_IS_REVERT", "no") == "yes"
if is_revert:
    print("Git revert detected → skipping Execute DDL & backups")
    sys.exit(0)

DDL_ARTIFACT = "ddl_output.json"

# =================================================
# Load Artifact
# =================================================
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

# =================================================
# Connect to Databricks
# =================================================
conn = sql.connect(
    server_hostname=os.environ["DATABRICKS_HOST"],
    http_path=os.environ["DATABRICKS_HTTP_PATH"],
    access_token=os.environ["DATABRICKS_TOKEN"],
)

cursor = conn.cursor()
cursor.execute("USE CATALOG hive_metastore")
print("Catalog set")

# =================================================
# Helpers
# =================================================
def strip_comments(sql_text):
    sql_text = re.sub(r"/\*.*?\*/", "", sql_text, flags=re.DOTALL)
    sql_text = re.sub(r"--.*", "", sql_text)
    return sql_text.strip()

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
# Detect Irreversible DDL
# =================================================
def is_irreversible(ddl_upper):

    irreversible_patterns = [
        "DROP COLUMN",
        "DROP TABLE",
        "REPLACE COLUMNS",
        "ALTER COLUMN TYPE"
    ]

    return any(p in ddl_upper for p in irreversible_patterns)

# =================================================
# Dialect Validator
# =================================================
UNSUPPORTED_KEYWORDS = [
    "ALTER INDEX",
    "SEQUENCE",
    "TRIGGER",
    "TABLESPACE",
    "ATTACH PARTITION",
    "DETACH PARTITION",
    "ALTER DATABASE",
    "ENABLE ROW LEVEL SECURITY",
    "UNLOGGED",
    "SWITCH TO",
]

def validate_sql_dialect(ddl_sql):
    ddl_upper = ddl_sql.upper()
    for kw in UNSUPPORTED_KEYWORDS:
        if kw in ddl_upper:
            raise Exception(f"Unsupported SQL for Databricks Delta: {kw}")

# =================================================
# Column Mapping
# =================================================
def needs_column_mapping(ddl_upper: str) -> bool:
    patterns = [
        "RENAME COLUMN",
        "CHANGE COLUMN",
        "DROP COLUMN",
        "REPLACE COLUMNS",
        "ALTER COLUMN",
    ]
    return any(p in ddl_upper for p in patterns)

def ensure_column_mapping_enabled(cursor, table_name):
    cursor.execute(f"SHOW TBLPROPERTIES {table_name}")
    props = {row[0]: row[1] for row in cursor.fetchall()}
    mode = props.get("delta.columnMapping.mode")

    if mode == "name":
        print(f"Column mapping already enabled for {table_name}")
        return

    print(f"Enabling column mapping for {table_name}...")
    cursor.execute(f"""
        ALTER TABLE {table_name}
        SET TBLPROPERTIES ('delta.columnMapping.mode' = 'name')
    """)
    print(f"Column mapping enabled for {table_name}")

# =================================================
# ALTER TYPE SAFE MIGRATION
# =================================================
def parse_alter_type(ddl_sql):
    pattern = r"ALTER TABLE\s+(\S+)\s+ALTER COLUMN\s+(\S+)\s+TYPE\s+(.+)"
    match = re.search(pattern, ddl_sql, re.IGNORECASE)
    if match:
        return match.group(1), match.group(2), match.group(3).strip()
    return None, None, None

def generate_migration_sql(table, column, new_type):
    tmp_col = f"{column}__tmp"
    return [
        f"ALTER TABLE {table} ADD COLUMN {tmp_col} {new_type}",
        f"UPDATE {table} SET {tmp_col} = CAST({column} AS {new_type})",
        f"ALTER TABLE {table} DROP COLUMN {column}",
        f"ALTER TABLE {table} RENAME COLUMN {tmp_col} TO {column}"
    ]

# =================================================
# Check if backup required
# =================================================
backup_required = False

for item in ddls:

    ddl_sql = strip_comments(item["statement"])
    ddl_upper = ddl_sql.upper()

    if is_irreversible(ddl_upper):
        backup_required = True
        break

# =================================================
# Create Backup Table
# =================================================
if backup_required:

    print("Irreversible or mixed DDL detected → creating backup")

    tables_to_backup = set()

    for item in ddls:
        table_name = extract_table_name(item["statement"])
        if table_name:
            tables_to_backup.add(table_name)

    for table in tables_to_backup:

        table_name = table.split('.')[-1]

        source_table = f"hive_metastore.default.{table_name}"
        backup_table = f"hive_metastore.ddl_backup_table.{table_name}_backup_{commit_id}"

        print(f"Source table: {source_table}")
        print(f"Backup table: {backup_table}")

        cursor.execute(f"""
        CREATE TABLE {backup_table}
        DEEP CLONE {source_table}
        """)

else:
    print("All DDL reversible → skipping backup creation")

# =================================================
# Execute DDLs
# =================================================
failed = False
error_msg = None

for item in ddls:

    ddl_sql = strip_comments(item["statement"])
    ddl_upper = ddl_sql.upper()

    try:
        validate_sql_dialect(ddl_sql)

        table_name = extract_table_name(ddl_sql)

        if table_name and needs_column_mapping(ddl_upper):
            ensure_column_mapping_enabled(cursor, table_name)

        print("\nExecuting DDL:")
        print(ddl_sql)

        if "ALTER TABLE" in ddl_upper and "ALTER COLUMN" in ddl_upper and "TYPE" in ddl_upper:

            table, column, new_type = parse_alter_type(ddl_sql)

            print("Using safe migration strategy for ALTER TYPE")

            migration_sql = generate_migration_sql(table, column, new_type)

            for stmt in migration_sql:
                print(f"Executing: {stmt}")
                cursor.execute(stmt)

        else:
            cursor.execute(ddl_sql)

        cursor.execute(f"""
          INSERT INTO hive_metastore.default.ddl_audit_log VALUES (
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