import os
import requests
import base64
import re
from databricks import sql

print("Starting rollback execution...")

DATABRICKS_HOST = os.environ["DATABRICKS_HOST"]
DATABRICKS_TOKEN = os.environ["DATABRICKS_TOKEN"]
DATABRICKS_HTTP_PATH = os.environ["DATABRICKS_HTTP_PATH"]
REVERT_COMMIT = os.environ["REVERT_COMMIT"]

WORKSPACE_PATH = f"/rollback_scripts/rollback_{REVERT_COMMIT}.sql"

# ----------------------------------------
# Fetch rollback SQL from workspace
# ----------------------------------------

url = f"{DATABRICKS_HOST}/api/2.0/workspace/export"

print(f"Fetching rollback script from workspace: {WORKSPACE_PATH}")

response = requests.get(
    url,
    headers={"Authorization": f"Bearer {DATABRICKS_TOKEN}"},
    params={"path": WORKSPACE_PATH, "format": "SOURCE"}
)

if response.status_code != 200:
    print("Rollback file not found")
    exit(1)

# ----------------------------------------
#  Decode base64 content
# ----------------------------------------

data = response.json()

encoded = data.get("content")

if not encoded:
    print("Empty rollback content")
    exit(1)

sql_text = base64.b64decode(encoded).decode("utf-8")

print("Rollback file downloaded and decoded successfully")

# ----------------------------------------
# Clean notebook format
# ----------------------------------------
sql_text = sql_text.replace("-- Databricks notebook source", "")
sql_text = sql_text.replace("-- COMMAND ----------", "")

# ----------------------------------------
# Split statements
# ----------------------------------------

statements = [
    s.strip()
    for s in sql_text.split(";")
    if s.strip()
]

print(f"Executing {len(statements)} rollback statements")

# ----------------------------------------
# Connect to Databricks
# ----------------------------------------

conn = sql.connect(
    server_hostname=DATABRICKS_HOST.replace("https://", ""),
    http_path=DATABRICKS_HTTP_PATH,
    access_token=DATABRICKS_TOKEN
)

cursor = conn.cursor()

# ----------------------------------------
# Helpers
# ----------------------------------------

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

def strip_hive_metastore_prefix(value):
    if not value:
        return value

    return re.sub(r"(?i)\bhive_metastore\.", "", value)

def split_schema_and_table(table_name):
    table_name = strip_hive_metastore_prefix(table_name)

    if not table_name:
        return None, None

    parts = table_name.split(".")
    if len(parts) >= 2:
        return ".".join(parts[:-1]), parts[-1]

    return None, table_name

def sanitize_statement_for_non_uc(stmt):
    sanitized = re.sub(
        r"(?i)\bhive_metastore\.([A-Za-z_][\w]*)\.([A-Za-z_][\w]*)",
        r"\1.\2",
        stmt
    )
    sanitized = re.sub(r"(?i)\bhive_metastore\.", "", sanitized)
    return sanitized

def find_table_schema(cursor, table_name):
    _, base_table_name = split_schema_and_table(table_name)

    try:
        cursor.execute("SHOW DATABASES")
        schemas = cursor.fetchall()

        for schema in schemas:
            schema_name = schema[0]
            cursor.execute(f"SHOW TABLES IN {schema_name}")
            tables = cursor.fetchall()

            for t in tables:
                if t[1] == base_table_name:
                    return schema_name

    except Exception as e:
        print(f"Schema detection skipped for {table_name}: {e}", flush=True)

    return None

def needs_column_mapping(ddl_upper):
    patterns = [
        "RENAME COLUMN",
        "CHANGE COLUMN",
        "DROP COLUMN",
        "REPLACE COLUMNS",
        "ALTER COLUMN"
    ]

    return any(p in ddl_upper for p in patterns)

def ensure_column_mapping_enabled(cursor, table_name, schema):
    table_name = strip_hive_metastore_prefix(table_name)
    schema = strip_hive_metastore_prefix(schema)
    full_table = f"{schema}.{table_name}" if schema else table_name

    try:
        cursor.execute(f"SHOW TBLPROPERTIES {full_table}")
        props = {row[0]: row[1] for row in cursor.fetchall()}
    except Exception as e:
        print(
            f"Column mapping check skipped for {full_table}: {e}",
            flush=True
        )
        return False

    if props.get("delta.columnMapping.mode") == "name":
        return True

    try:
        print(f"Enabling column mapping for {full_table}", flush=True)
        cursor.execute(f"""
            ALTER TABLE {full_table}
            SET TBLPROPERTIES ('delta.columnMapping.mode'='name')
        """)
        return True
    except Exception as e:
        print(
            f"Column mapping enable skipped for {full_table}: {e}",
            flush=True
        )
        return False

def is_alter_column_type_statement(ddl_sql):
    normalized_sql = re.sub(r"\s+", " ", ddl_sql.strip()).upper()
    return (
        normalized_sql.startswith("ALTER TABLE ")
        and " ALTER COLUMN " in normalized_sql
        and " TYPE " in normalized_sql
    ) or (
        normalized_sql.startswith("ALTER TABLE ")
        and " CHANGE COLUMN " in normalized_sql
        and " TYPE " in normalized_sql
    )

def rewrite_alter_column_type(ddl_sql):
    normalized_sql = re.sub(r"\s+", " ", ddl_sql.strip())
    pattern = r"ALTER\s+TABLE\s+([^\s]+)\s+(?:ALTER|CHANGE)\s+COLUMN\s+([^\s]+)\s+TYPE\s+([^\s;]+)"
    match = re.search(pattern, normalized_sql, re.IGNORECASE)

    if not match:
        return None

    table = match.group(1)
    column = match.group(2)
    new_type = match.group(3)
    temp_col = f"{column}_new"

    print(f"Applying Delta migration rule for rollback column type change: {column}", flush=True)

    return [
        f"ALTER TABLE {table} ADD COLUMN {temp_col} {new_type}",
        f"UPDATE {table} SET {temp_col} = CAST({column} AS {new_type})",
        f"ALTER TABLE {table} DROP COLUMN {column}",
        f"ALTER TABLE {table} RENAME COLUMN {temp_col} TO {column}"
    ]

# ----------------------------------------
# Execute statements
# ----------------------------------------

for stmt in statements:
    stmt = sanitize_statement_for_non_uc(stmt)
    ddl_upper = stmt.upper()

    if ddl_upper.startswith("USE CATALOG"):
        print(f"Skipping catalog switch during rollback: {stmt}", flush=True)
        continue

    if ddl_upper.startswith("USE SCHEMA"):
        print(f"Switching context: {stmt}", flush=True)
        cursor.execute(stmt)
        continue

    table_name = extract_table_name(stmt)
    schema = None

    if table_name:
        schema, base_table_name = split_schema_and_table(table_name)

        if not schema:
            schema = find_table_schema(cursor, table_name)

        if schema and "." not in table_name:
            stmt = stmt.replace(table_name, f"{schema}.{base_table_name}", 1)
            table_name = base_table_name

        if needs_column_mapping(ddl_upper):
            ensure_column_mapping_enabled(cursor, table_name, schema)

    if is_alter_column_type_statement(stmt):
        rewritten = rewrite_alter_column_type(stmt)
        if not rewritten:
            raise Exception(f"Failed to rewrite ALTER COLUMN TYPE rollback statement: {stmt}")

        for rewritten_stmt in rewritten:
            print(f"Executing rewritten rollback step: {rewritten_stmt}", flush=True)
            cursor.execute(rewritten_stmt)
        continue

    print(f"Running: {stmt}")
    cursor.execute(stmt)

print("Rollback executed successfully")

cursor.close()
conn.close()
