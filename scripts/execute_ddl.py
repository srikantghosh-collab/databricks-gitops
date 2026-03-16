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
    access_token=os.environ["DATABRICKS_TOKEN"]
)

print("Connection object created", flush=True)

cursor = conn.cursor()
print("Cursor created", flush=True)

cursor.execute("SELECT 1")
print("Test query executed", flush=True)

# =================================================
# Ensure migration tracking table exists
# =================================================

print("Ensuring ddl_execution_log table exists...", flush=True)

cursor.execute("""
CREATE TABLE IF NOT EXISTS hive_metastore.default.ddl_execution_log (
    script_name STRING,
    status STRING,
    last_executed_cell INT,
    executed_at TIMESTAMP
)
USING DELTA
""")

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


def find_table_schema(cursor, table_name):

    try:
        cursor.execute("SHOW DATABASES")
        schemas = cursor.fetchall()

        for schema in schemas:

            schema_name = schema[0]

            cursor.execute(f"SHOW TABLES IN {schema_name}")
            tables = cursor.fetchall()

            for t in tables:
                if t[1] == table_name:
                    return schema_name

    except Exception as e:
        print(f"Schema detection skipped for {table_name}: {e}", flush=True)

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


# =================================================
# Delta Migration Rule
# =================================================

def rewrite_alter_column_type(ddl_sql):

    pattern = r"ALTER\s+TABLE\s+([^\s]+)\s+ALTER\s+COLUMN\s+([^\s]+)\s+TYPE\s+([^\s;]+)"
    match = re.search(pattern, ddl_sql, re.IGNORECASE)

    if not match:
        return None

    table = match.group(1)
    column = match.group(2)
    new_type = match.group(3)

    temp_col = f"{column}_new"

    print(f"Applying Delta migration rule for column type change: {column}", flush=True)

    return [
        f"ALTER TABLE {table} ADD COLUMN {temp_col} {new_type}",
        f"UPDATE {table} SET {temp_col} = CAST({column} AS {new_type})",
        f"ALTER TABLE {table} DROP COLUMN {column}",
        f"ALTER TABLE {table} RENAME COLUMN {temp_col} TO {column}"
    ]


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


# =================================================
# FIXED: schema-aware column mapping
# =================================================

def ensure_column_mapping_enabled(cursor, table_name, schema):

    full_table = f"{schema}.{table_name}" if schema else table_name

    cursor.execute(f"SHOW TBLPROPERTIES {full_table}")

    props = {row[0]: row[1] for row in cursor.fetchall()}

    mode = props.get("delta.columnMapping.mode")

    if mode == "name":
        return

    print(f"Enabling column mapping for {full_table}")

    cursor.execute(f"""
        ALTER TABLE {full_table}
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

            if ddl_upper.startswith("USE SCHEMA") or ddl_upper.startswith("USE CATALOG"):
                print(f"Switching context: {ddl_sql}", flush=True)
                cursor.execute(ddl_sql)
                continue

            validate_sql_dialect(ddl_sql)

            table_name = extract_table_name(ddl_sql)

            schema = None

            if table_name and not ddl_upper.startswith("CREATE TABLE"):
                schema = find_table_schema(cursor, table_name)

                if schema:
                    print(f"Detected schema {schema} for table {table_name}", flush=True)

                    ddl_sql = ddl_sql.replace(
                        table_name,
                        f"{schema}.{table_name}",
                        1
                    )

            if table_name and needs_column_mapping(ddl_upper):
                ensure_column_mapping_enabled(cursor, table_name, schema)

            rewritten = rewrite_alter_column_type(ddl_sql)

            if rewritten:
                for stmt in rewritten:
                    print(f"Executing rewritten step: {stmt}", flush=True)
                    cursor.execute(stmt)
            else:
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
                    INSERT (script_name, status, last_executed_cell, executed_at)
                    VALUES ('{script_name}','RUNNING',{i+1},current_timestamp())
            """)

        except Exception as e:

            cursor.execute(f"""
                MERGE INTO hive_metastore.default.ddl_execution_log t
                USING (SELECT '{script_name}' AS script_name) s
                ON t.script_name = s.script_name
                WHEN MATCHED THEN
                    UPDATE SET
                        status='FAILED',
                        last_executed_cell={i},
                        executed_at=current_timestamp()
                WHEN NOT MATCHED THEN
                    INSERT (script_name, status, last_executed_cell, executed_at)
                    VALUES ('{script_name}','FAILED',{i},current_timestamp())
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
            INSERT (script_name, status, last_executed_cell, executed_at)
            VALUES ('{script_name}','SUCCESS',{len(statements)},current_timestamp())
    """)

cursor.close()
conn.close()

print("\nAll DDL migration scripts executed successfully")