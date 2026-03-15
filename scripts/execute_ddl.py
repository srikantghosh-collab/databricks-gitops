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
    print("Git revert detected → skipping Execute DDL")
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

migrations = payload.get("migrations", [])

if not migrations:
    print("No migration scripts to execute — exiting")
    sys.exit(0)

# enforce migration order
migrations = sorted(migrations, key=lambda x: x["script_name"])

commit_id = payload.get("commit_id") or subprocess.check_output(
    ["git", "rev-parse", "HEAD"], text=True
).strip()

print(f"Commit ID: {commit_id}")

# =================================================
# Connect to Databricks
# =================================================

print("Connecting to Databricks...", flush=True)
conn = sql.connect(
    server_hostname=os.environ["DATABRICKS_HOST"],
    http_path=os.environ["DATABRICKS_HTTP_PATH"],
    auth_type="oauth-m2m",
    azure_client_id=os.environ["DATABRICKS_CLIENT_ID"],
    azure_client_secret=os.environ["CLIENT_SECRET"],
    azure_tenant_id=os.environ["TENANT_ID"],
    _timeout=30
)

cursor = conn.cursor()

cursor.execute("USE CATALOG hive_metastore")

print("Connected to Databricks", flush=True)

# =================================================
# Helpers
# =================================================

def strip_comments(sql_text):
    sql_text = re.sub(r"/\*.*?\*/", "", sql_text, flags=re.DOTALL)
    sql_text = re.sub(r"--.*", "", sql_text)
    return sql_text.strip()


def read_sql_file(path):

    with open(path) as f:
        sql_text = f.read()

    statements = []

    for stmt in sql_text.split(";"):
        stmt = strip_comments(stmt).strip()
        if stmt:
            statements.append(stmt)

    return statements


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


def get_execution_status(cursor, script_name):

    cursor.execute(f"""
        SELECT status, last_executed_cell
        FROM hive_metastore.default.ddl_execution_log
        WHERE script_name = '{script_name}'
    """)

    row = cursor.fetchone()

    if row:
        return row[0], row[1]

    return None, 0


UNSUPPORTED_KEYWORDS = [
    "ALTER INDEX",
    "SEQUENCE",
    "TRIGGER",
    "TABLESPACE",
    "ATTACH PARTITION",
    "DETACH PARTITION",
    "ALTER DATABASE",
    "ENABLE ROW LEVEL SECURITY",
]

def validate_sql_dialect(ddl_sql):

    ddl_upper = ddl_sql.upper()

    for kw in UNSUPPORTED_KEYWORDS:
        if kw in ddl_upper:
            raise Exception(f"Unsupported SQL for Databricks Delta: {kw}")


def needs_column_mapping(ddl_upper: str):

    patterns = [
        "RENAME COLUMN",
        "CHANGE COLUMN",
        "DROP COLUMN",
        "REPLACE COLUMNS",
        "ALTER COLUMN"
    ]

    return any(p in ddl_upper for p in patterns)


def ensure_column_mapping_enabled(cursor, table_name):

    cursor.execute(f"SHOW TBLPROPERTIES {table_name}")

    props = {row[0]: row[1] for row in cursor.fetchall()}

    mode = props.get("delta.columnMapping.mode")

    if mode == "name":
        return

    print(f"Enabling column mapping for {table_name}")

    cursor.execute(f"""
        ALTER TABLE {table_name}
        SET TBLPROPERTIES ('delta.columnMapping.mode'='name')
    """)


# =================================================
# Execute Migrations
# =================================================

for migration in migrations:

    script_name = migration["script_name"]
    script_path = migration["path"]

    print(f"\nProcessing migration: {script_name}", flush=True)

    status, last_cell = get_execution_status(cursor, script_name)

    if status == "SUCCESS":
        print("Already executed → skipping")
        continue

    statements = read_sql_file(script_path)

    for i, ddl_sql in enumerate(statements):

        if i < last_cell:
            continue

        ddl_upper = ddl_sql.upper()

        try:

            validate_sql_dialect(ddl_sql)

            table_name = extract_table_name(ddl_sql)

            if table_name and needs_column_mapping(ddl_upper):
                ensure_column_mapping_enabled(cursor, table_name)

            print(f"Executing cell {i+1}", flush=True)

            cursor.execute(ddl_sql)

            cursor.execute(f"""
                MERGE INTO hive_metastore.default.ddl_execution_log t
                USING (SELECT '{script_name}' AS script_name) s
                ON t.script_name = s.script_name
                WHEN MATCHED THEN
                    UPDATE SET
                        status='RUNNING',
                        last_executed_cell={i+1},
                        executed_at=current_timestamp()
                WHEN NOT MATCHED THEN
                    INSERT VALUES
                    ('{script_name}','RUNNING',{i+1},current_timestamp())
            """)

        except Exception as e:

            cursor.execute(f"""
                MERGE INTO hive_metastore.default.ddl_execution_log t
                USING (SELECT '{script_name}' AS script_name) s
                ON t.script_name = s.script_name
                WHEN MATCHED THEN
                    UPDATE SET
                        status='FAILED',
                        last_executed_cell={i}
            """)

            cursor.close()
            conn.close()

            raise e

    cursor.execute(f"""
        MERGE INTO hive_metastore.default.ddl_execution_log t
        USING (SELECT '{script_name}' AS script_name) s
        ON t.script_name = s.script_name
        WHEN MATCHED THEN
            UPDATE SET
                status='SUCCESS',
                last_executed_cell={len(statements)},
                executed_at=current_timestamp()
        WHEN NOT MATCHED THEN
            INSERT VALUES
            ('{script_name}','SUCCESS',{len(statements)},current_timestamp())
    """)

cursor.close()
conn.close()

print("\nAll DDL migration scripts executed successfully")