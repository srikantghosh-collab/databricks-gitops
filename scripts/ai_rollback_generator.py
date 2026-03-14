import json
import os
import sys
import re
from openai import AzureOpenAI
from databricks import sql

print("Starting AI rollback generation...")

DDL_ARTIFACT = "ddl_output.json"

# ----------------------------------------
# Validate artifact
# ----------------------------------------

if not os.path.exists(DDL_ARTIFACT):
    print("DDL artifact not found")
    open("rollback.sql", "w").close()
    sys.exit(0)

with open(DDL_ARTIFACT) as f:
    payload = json.load(f)

migrations = payload.get("migrations", [])
commit_id = payload.get("commit_id")

if not migrations:
    print("No migration scripts found")
    open("rollback.sql", "w").close()
    sys.exit(0)

# ----------------------------------------
# Azure OpenAI Client
# ----------------------------------------

client = AzureOpenAI(
    api_key=os.environ["AZURE_OPENAI_KEY"],
    api_version="2024-02-15-preview",
    azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
)

# ----------------------------------------
# Databricks Connection (Service Principal)
# ----------------------------------------

conn = sql.connect(
    server_hostname=os.environ["DATABRICKS_HOST"],
    http_path=os.environ["DATABRICKS_HTTP_PATH"],
    auth_type="azure-client-secret",
    azure_client_id=os.environ["DATABRICKS_CLIENT_ID"],
    azure_client_secret=os.environ["CLIENT_SECRET"],
    azure_tenant_id=os.environ["TENANT_ID"],
)

cursor = conn.cursor()

# ----------------------------------------
# System Prompt
# ----------------------------------------

SYSTEM_PROMPT = """You are an expert Databricks Delta Lake database reliability engineer.

Your task is to generate ONLY the rollback SQL for the given DDL statements.

You are also provided with table metadata retrieved from the Databricks system catalog.
Use this metadata to reconstruct the previous table structure when generating rollback SQL.

--------------------------------------------------
STRICT OUTPUT RULES
--------------------------------------------------

1. Output ONLY executable rollback SQL statements.
2. Do NOT include the original DDL statements.
3. Do NOT include explanations or headers.
4. Do NOT include metadata or comments except one case:
-- ROLLBACK NOT POSSIBLE
5. Statements must be executable in Databricks SQL.
6. Never hardcode table names. Use the names from the input DDL.
7. Rollback statements MUST appear in REVERSE ORDER of the forward DDL statements.
8. Process each DDL statement independently.
9. Use the provided table metadata to reconstruct rollback SQL whenever possible.
10. Only output:
-- ROLLBACK NOT POSSIBLE
if the rollback truly cannot be determined even using the provided metadata.

If some statements cannot be reversed, still generate rollback SQL
for all reversible statements.

Do not mark the entire rollback as impossible if only some
statements cannot be reversed.

--------------------------------------------------
METADATA USAGE RULE
--------------------------------------------------

You are provided with table metadata retrieved from the system catalog.

This metadata contains the table schema including column names and types.

Use this metadata to reconstruct rollback SQL for operations such as:

- DROP COLUMN
- ALTER COLUMN TYPE
- DROP TABLE
- REPLACE COLUMNS
- Schema modifications

If metadata allows reconstruction, generate rollback SQL instead of
marking the operation as irreversible.

--------------------------------------------------
CREATE TABLE SPECIAL RULE
--------------------------------------------------

If CREATE TABLE appears as the first statement AND the table did not exist before the commit,
the rollback must be exactly:

DROP TABLE table_name;

If the table already existed before the commit:
DO NOT drop the table.

Ignore the CREATE TABLE statement and generate rollback SQL
for the remaining DDL statements in reverse order.

--------------------------------------------------
DDL → ROLLBACK RULES
--------------------------------------------------

CREATE TABLE
Rollback:
DROP TABLE table_name;

DROP TABLE
Rollback:
Recreate the table using the provided metadata schema.
Example:
CREATE TABLE table_name (
column1 TYPE,
column2 TYPE
)
USING DELTA;

ALTER TABLE ADD COLUMN column_name TYPE
Rollback:
ALTER TABLE table_name DROP COLUMN column_name;

ALTER TABLE ADD COLUMNS (col1 TYPE, col2 TYPE, ...)
Rollback:
ALTER TABLE table_name DROP COLUMN col1;
ALTER TABLE table_name DROP COLUMN col2;

ALTER TABLE RENAME COLUMN old_name TO new_name
Rollback:
ALTER TABLE table_name RENAME COLUMN new_name TO old_name;

ALTER TABLE DROP COLUMN column_name
Rollback:
Recreate the column using metadata.
Example:
ALTER TABLE table_name ADD COLUMN column_name column_type;

ALTER TABLE ALTER COLUMN column_name SET NOT NULL
Rollback:
ALTER TABLE table_name ALTER COLUMN column_name DROP NOT NULL;

ALTER TABLE ALTER COLUMN column_name DROP NOT NULL
Rollback:
ALTER TABLE table_name ALTER COLUMN column_name SET NOT NULL;

ALTER TABLE ALTER COLUMN column_name SET DEFAULT value
Rollback:
ALTER TABLE table_name ALTER COLUMN column_name DROP DEFAULT;

ALTER TABLE ALTER COLUMN column_name DROP DEFAULT
Rollback:
Restore the previous default value if available from metadata.

ALTER TABLE ALTER COLUMN column_name TYPE new_type
Rollback:
ALTER TABLE table_name ALTER COLUMN column_name TYPE previous_type;

ALTER TABLE ALTER COLUMN column_name COMMENT 'text'
Rollback:
Restore the previous comment if available from metadata.

ALTER TABLE SET TBLPROPERTIES ('key'='value')
Rollback:
ALTER TABLE table_name UNSET TBLPROPERTIES ('key');

ALTER TABLE UNSET TBLPROPERTIES ('key')
Rollback:
Restore the previous property if metadata provides it.

ALTER TABLE RENAME TO new_table
Rollback:
ALTER TABLE new_table RENAME TO old_table;

ALTER TABLE REPLACE COLUMNS (...)
Rollback:
Recreate the previous schema using metadata.

ALTER TABLE CLUSTER BY (...)
Rollback:
Remove clustering configuration if possible.

ALTER TABLE SET LOCATION
Rollback:
Restore the previous location if available.

ALTER TABLE SET OWNER
Rollback:
Restore the previous owner if metadata provides it.

ALTER TABLE ADD CONSTRAINT constraint_name
Rollback:
ALTER TABLE table_name DROP CONSTRAINT constraint_name;

ALTER TABLE DROP CONSTRAINT constraint_name
Rollback:
Recreate the constraint if metadata provides its definition.

ALTER TABLE ENABLE CHANGE DATA FEED
Rollback:
ALTER TABLE table_name SET TBLPROPERTIES ('delta.enableChangeDataFeed'='false');

ALTER TABLE SET COMMENT
Rollback:
Restore the previous comment if available from metadata.

Return ONLY the rollback SQL statements in reverse order.
Use metadata to reconstruct rollback SQL whenever possible.
"""

# ----------------------------------------
# Helper: Extract table name
# ----------------------------------------

def extract_table_name(stmt):

    patterns = [
        r"CREATE\s+TABLE\s+(IF\s+NOT\s+EXISTS\s+)?([^\s(]+)",
        r"ALTER\s+TABLE\s+([^\s]+)",
        r"DROP\s+TABLE\s+(IF\s+EXISTS\s+)?([^\s]+)",
        r"INSERT\s+INTO\s+([^\s(]+)",
        r"UPDATE\s+([^\s]+)",
        r"MERGE\s+INTO\s+([^\s]+)"
    ]

    for p in patterns:
        m = re.search(p, stmt, re.IGNORECASE)
        if m:
            return m.group(m.lastindex)

    return None


# ----------------------------------------
# Fetch table schema
# ----------------------------------------

def get_table_schema(table):

    try:
        cursor.execute(f"DESCRIBE TABLE {table}")
        rows = cursor.fetchall()

        schema = [
            {"column": r[0], "type": r[1]}
            for r in rows if r[0] and not r[0].startswith("#")
        ]

        return schema

    except Exception:
        return None


# ----------------------------------------
# Read migration SQL files
# ----------------------------------------

forward_statements = []

for migration in migrations:

    path = migration["path"]

    if not os.path.exists(path):
        print(f"Warning: {path} not found")
        continue

    with open(path) as f:
        sql_text = f.read()

    statements = [
        s.strip()
        for s in sql_text.split(";")
        if s.strip()
    ]

    forward_statements.extend(statements)

if not forward_statements:
    print("No SQL statements detected in migrations")
    open("rollback.sql", "w").close()
    sys.exit(0)

print(f"Detected {len(forward_statements)} SQL statements")

# ----------------------------------------
# Build metadata payload
# ----------------------------------------

metadata_payload = []

for stmt in forward_statements:

    table = extract_table_name(stmt)

    schema = None
    if table:
        schema = get_table_schema(table)

    metadata_payload.append({
        "statement": stmt,
        "table": table,
        "schema": schema
    })

forward_sql_text = "\n".join(forward_statements)
metadata_text = json.dumps(metadata_payload, indent=2)

# ----------------------------------------
# Call Azure OpenAI
# ----------------------------------------

response = client.chat.completions.create(
    model=os.environ["AZURE_DEPLOYMENT_NAME"],
    temperature=0,
    messages=[
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"""
Forward DDL statements:

{forward_sql_text}

Table metadata:

{metadata_text}

Generate rollback SQL.
"""
        }
    ]
)

rollback_sql = response.choices[0].message.content.strip()

# ----------------------------------------
# Safety check
# ----------------------------------------

dangerous_patterns = [
    "DROP DATABASE",
    "TRUNCATE TABLE",
    "DELETE FROM"
]

for pattern in dangerous_patterns:
    if pattern in rollback_sql.upper():
        print(f"Unsafe rollback detected: {pattern}")
        sys.exit(1)

# ----------------------------------------
# Convert to notebook format
# ----------------------------------------

commands = [
    cmd.strip()
    for cmd in rollback_sql.split(";")
    if cmd.strip()
]

formatted_sql = "\n\n-- COMMAND ----------\n\n".join([c + ";" for c in commands])

# ----------------------------------------
# Write rollback.sql
# ----------------------------------------

rollback_path = os.path.join(
    os.environ.get("SYSTEM_DEFAULTWORKINGDIRECTORY", "."),
    "rollback.sql"
)

with open(rollback_path, "w") as f:
    f.write(formatted_sql)

cursor.close()
conn.close()

print(f"Rollback SQL generated successfully: {rollback_path}")