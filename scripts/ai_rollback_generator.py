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
# Connect to Databricks
# ----------------------------------------

print("Connecting to Databricks for schema detection...")

conn = sql.connect(
    server_hostname=os.environ["DATABRICKS_HOST"],
    http_path=os.environ["DATABRICKS_HTTP_PATH"],
    access_token=os.environ["DATABRICKS_TOKEN"]
)

cursor = conn.cursor()

# ----------------------------------------
# NEW: CURRENT SCHEMA FALLBACK
# ----------------------------------------

def get_current_schema(cursor):
    try:
        cursor.execute("SELECT current_schema()")
        return cursor.fetchone()[0]
    except Exception as e:
        print(f"Failed to fetch current schema: {e}")
        return None

# ----------------------------------------

def get_already_executed_scripts(cursor):
    try:
        cursor.execute("""
            SELECT script_name
            FROM hive_metastore.default.ddl_execution_log
            WHERE status = 'SUCCESS'
        """)
        return {row[0] for row in cursor.fetchall()}
    except Exception as e:
        print(f"Failed to fetch execution log: {e}")
        return set()

executed_scripts = get_already_executed_scripts(cursor)

migrations = [
    m for m in migrations
    if m["script_name"] not in executed_scripts
]

if not migrations:
    print("No new migrations to rollback")
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
# SYSTEM PROMPT (UNCHANGED)
# ----------------------------------------

SYSTEM_PROMPT = '''You are an expert Databricks Delta Lake database reliability engineer.

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

7. Process the DDL statements as a SEQUENTIAL execution track.
   You must treat the input as an ordered execution log
   Rollback MUST strictly follow stack reversal:
   - Last executed statement must be the first rollback statement.
   - First executed statement must be the last rollback statement.
   Do NOT group, reorder, or optimize statements.
   DO NOT change order based on logic.

8. DO NOT reorder statements based on logic or grouping.
   Maintain exact 1-to-1 reverse mapping for each statement.

9. Each rollback statement must correspond directly to its forward statement.

10. You MUST attempt rollback for EVERY DDL statement.

11. If one statement cannot be reversed, still generate rollback SQL for all other statements.

12. DO NOT insert '-- ROLLBACK NOT POSSIBLE' between valid rollback statements.

13. ORDER ENFORCEMENT RULE:
   
    You must preserve exact positional mapping:

     If input order is:
     1,2,3,4,5,6

     Output MUST be:
     6,5,4,3,2,1

     STRICTLY FOLLOW THIS IF SOME STATEMENTS SEEM INDEPENDENT.

14. TABLE LIFECYCLE ORDER RULE:

Keep strict reverse order as the default.

Apply only these dependency-safe exceptions:

- If a rollback statement is DROP TABLE generated from a forward CREATE TABLE,
  place that DROP TABLE after every other rollback statement for the same table.
- If a rollback statement is CREATE TABLE generated from a forward DROP TABLE,
  place that CREATE TABLE before any rollback statement that references that same table.

Do NOT move CREATE TABLE or DROP TABLE statements to the top just because they are table-level operations.
Only adjust order when required so dependent ALTER TABLE rollback statements can execute safely.

--------------------------------------------------
METADATA USAGE RULE
--------------------------------------------------

You are provided with table metadata retrieved from the system catalog.

This metadata contains the current table schema including column names and types.

Use this metadata to reconstruct rollback SQL whenever possible.

If metadata is insufficient:

Infer missing information from earlier DDL statements.
DO NOT guess random values.
DO NOT output placeholders like 'previous_type'.

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

CREATE TABLE IF NOT EXISTS:
Always assume the table is newly created in this migration.

Rollback MUST be:
DROP TABLE table_name;

IMPORTANT:
DO NOT generate DROP TABLE unless a CREATE TABLE statement exists in the input.

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

--------------------------------------------------

ALTER TABLE ADD COLUMN column_name TYPE
Rollback:
ALTER TABLE table_name DROP COLUMN column_name;

This operation is ALWAYS reversible.
NEVER mark as ROLLBACK NOT POSSIBLE.

--------------------------------------------------

ALTER TABLE ADD COLUMNS (col1 TYPE, col2 TYPE, ...)
Rollback:
ALTER TABLE table_name DROP COLUMN col1;
ALTER TABLE table_name DROP COLUMN col2;

--------------------------------------------------

ALTER TABLE RENAME COLUMN old_name TO new_name
Rollback:
ALTER TABLE table_name RENAME COLUMN new_name TO old_name;

--------------------------------------------------

ALTER TABLE DROP COLUMN column_name
Rollback:
Recreate the column using metadata.

Example:
ALTER TABLE table_name ADD COLUMN column_name column_type;

If metadata does NOT contain the column type:
Infer the column type from earlier DDL statements.

DO NOT skip this statement.

--------------------------------------------------

ALTER TABLE ALTER COLUMN column_name TYPE new_type
Rollback:
ALTER TABLE table_name ALTER COLUMN column_name TYPE previous_type;

If previous type is not available in metadata:
Infer it from earlier DDL statements.

DO NOT output placeholders like 'previous_type'.

--------------------------------------------------

ALTER TABLE ALTER COLUMN column_name SET NOT NULL
Rollback:
ALTER TABLE table_name ALTER COLUMN column_name DROP NOT NULL;

ALTER TABLE ALTER COLUMN column_name DROP NOT NULL
Rollback:
ALTER TABLE table_name ALTER COLUMN column_name SET NOT NULL;

--------------------------------------------------

ALTER TABLE ALTER COLUMN column_name SET DEFAULT value
Rollback:
ALTER TABLE table_name ALTER COLUMN column_name DROP DEFAULT;

ALTER TABLE ALTER COLUMN column_name DROP DEFAULT
Rollback:
Restore previous default if available.

--------------------------------------------------

ALTER TABLE ALTER COLUMN column_name COMMENT 'text'
Rollback:
Restore previous comment if available.

--------------------------------------------------

ALTER TABLE SET TBLPROPERTIES ('key'='value')
Rollback:
ALTER TABLE table_name UNSET TBLPROPERTIES ('key');

ALTER TABLE UNSET TBLPROPERTIES ('key')
Rollback:
Restore previous property if metadata provides it.

--------------------------------------------------

ALTER TABLE RENAME TO new_table
Rollback:
ALTER TABLE new_table RENAME TO old_table;

--------------------------------------------------

ALTER TABLE REPLACE COLUMNS (...)
Rollback:
Recreate the previous schema using metadata.

--------------------------------------------------

ALTER TABLE CLUSTER BY (...)
Rollback:
Remove clustering configuration if possible.

--------------------------------------------------

ALTER TABLE SET LOCATION
Rollback:
Restore previous location if available.

--------------------------------------------------

ALTER TABLE SET OWNER
Rollback:
Restore previous owner if metadata provides it.

--------------------------------------------------

ALTER TABLE ADD CONSTRAINT constraint_name
Rollback:
ALTER TABLE table_name DROP CONSTRAINT constraint_name;

ALTER TABLE DROP CONSTRAINT constraint_name
Rollback:
Recreate constraint if metadata provides definition.

--------------------------------------------------

ALTER TABLE ENABLE CHANGE DATA FEED
Rollback:
ALTER TABLE table_name SET TBLPROPERTIES ('delta.enableChangeDataFeed'='false');

--------------------------------------------------

ALTER TABLE SET COMMENT
Rollback:
Restore previous comment if available.

--------------------------------------------------

Return ONLY the rollback SQL statements in STRICT reverse order.
Use metadata and DDL inference wherever required.'''

# ----------------------------------------
# Extract table name
# ----------------------------------------

def extract_table_name(stmt):

    patterns = [
        r"CREATE\s+TABLE\s+(IF\s+NOT\s+EXISTS\s+)?([^\s(]+)",
        r"ALTER\s+TABLE\s+([^\s]+)",
        r"DROP\s+TABLE\s+(IF\s+EXISTS\s+)?([^\s]+)"
    ]

    for p in patterns:
        m = re.search(p, stmt, re.IGNORECASE)
        if m:
            full_name = m.group(m.lastindex)

            if "." in full_name:
                return full_name.split(".")[-1]

            return full_name

    return None

def normalize_rollback_command_order(commands):
    ordered = commands[:]

    i = 0
    while i < len(ordered):
        cmd = ordered[i]
        table = extract_table_name(cmd)

        if table and re.match(r"^\s*CREATE\s+TABLE\b", cmd, re.IGNORECASE):
            target_index = i

            for j in range(i - 1, -1, -1):
                prev_table = extract_table_name(ordered[j])
                if prev_table == table:
                    target_index = j

            if target_index != i:
                create_cmd = ordered.pop(i)
                ordered.insert(target_index, create_cmd)
                i = max(target_index, 0)
                continue

        i += 1

    i = 0
    while i < len(ordered):
        cmd = ordered[i]
        table = extract_table_name(cmd)

        if table and re.match(r"^\s*DROP\s+TABLE\b", cmd, re.IGNORECASE):
            target_index = i

            for j in range(i + 1, len(ordered)):
                next_table = extract_table_name(ordered[j])
                if next_table == table:
                    target_index = j

            if target_index != i:
                drop_cmd = ordered.pop(i)
                ordered.insert(target_index, drop_cmd)
                continue

        i += 1

    return ordered

# ----------------------------------------
# Detect schema
# ----------------------------------------

def detect_table_schema(table_name):

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
        print(f"Schema detection failed for {table_name}: {e}")

    return None

# ----------------------------------------
# Read migrations
# ----------------------------------------

forward_statements = []

for migration in migrations:

    path = migration["path"]

    if not os.path.exists(path):
        continue

    with open(path) as f:
        sql_text = f.read()

    statements = [
        s.strip()
        for s in sql_text.split(";")
        if s.strip()
    ]

    forward_statements.extend(statements)

DDL_KEYWORDS = ("CREATE", "ALTER", "DROP","USE")

forward_statements = [
    s for s in forward_statements
    if s.upper().startswith(DDL_KEYWORDS)
]

print(f"Detected {len(forward_statements)} DDL statements")


# ----------------------------------------
# Detect schema from SQL (IMPORTANT FIX)
# ----------------------------------------

def extract_schema_from_sql(statements):
    for stmt in statements:
        match = re.search(r"USE\s+SCHEMA\s+([^\s;]+)", stmt, re.IGNORECASE)
        if match:
            return match.group(1)
    return None

def extract_catalog_from_sql(statements):
    for stmt in statements:
        match = re.search(r"USE\s+CATALOG\s+([^\s;]+)", stmt, re.IGNORECASE)
        if match:
            return match.group(1)
    return None


detected_schema = extract_schema_from_sql(forward_statements)
detected_catalog = extract_catalog_from_sql(forward_statements)

if detected_catalog:
    print(f"Using catalog from SQL: {detected_catalog}")
    cursor.execute(f"USE CATALOG {detected_catalog}")

if detected_schema:
    print(f"Using schema from SQL: {detected_schema}")
    cursor.execute(f"USE SCHEMA {detected_schema}")


# ----------------------------------------
# Build metadata payload
# ----------------------------------------

metadata_payload = []

for stmt in forward_statements:

    table = extract_table_name(stmt)

    schema = None

    if table:
        schema = detect_table_schema(table)

        if not schema:
            schema = detected_schema

        if not schema:
            schema = get_current_schema(cursor)

        print(f"DEBUG → table={table}, schema={schema}")

    if table and schema:
        stmt = re.sub(
            rf"(?<!\.)\b{table}\b",
            f"{schema}.{table}",
            stmt
        )

 
        metadata_payload.append({
          "statement": stmt,
          "table": table,
          "schema": schema
        })

rollback_statements = []

forward_sql_text = "\n".join([m["statement"] for m in metadata_payload])

print("Sending full DDL to AI...", flush=True)

response = client.chat.completions.create(
    model=os.environ["AZURE_DEPLOYMENT_NAME"],
    temperature=0,
    timeout=60,
    messages=[
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": forward_sql_text}
    ]
)

rollback_sql = response.choices[0].message.content.strip()

# cleanup (IMPORTANT FIX)
rollback_sql = re.sub(r"```[\w]*", "", rollback_sql)
rollback_sql = rollback_sql.replace("```", "").strip()

print("AI rollback generated:\n", rollback_sql, flush=True)
# forward_sql_text = "\n".join([m["statement"] for m in metadata_payload])

# response = client.chat.completions.create(
#     model=os.environ["AZURE_DEPLOYMENT_NAME"],
#     temperature=0,
#     timeout=60,
#     messages=[
#         {"role": "system", "content": SYSTEM_PROMPT},
#         {"role": "user", "content": forward_sql_text}
#     ]
# )

# rollback_sql = response.choices[0].message.content.strip()

# # cleanup
# result = re.sub(r"```[\w]*", "", rollback_sql)
# result = result.replace("```", "").strip()

# rollback_statements.append(result)

# # final combine
# rollback_sql = "\n".join(rollback_statements)


# ----------------------------------------
# Inject schema in rollback
# ----------------------------------------

for item in metadata_payload:

    table = item["table"]
    schema = item["schema"]

    if table and schema:
        rollback_sql = re.sub(
            rf"(?<!\.)\b{table}\b",
            f"{schema}.{table}",
            rollback_sql
        )

# ----------------------------------------
# Convert to notebook format (FIXED)
# ----------------------------------------

# Normalize
rollback_sql = rollback_sql.replace("\r", "").strip()

# Robust split (handles newline + missing semicolon)
commands = re.split(r";\s*\n|;\s*$", rollback_sql)

commands = [cmd.strip() for cmd in commands if cmd.strip()]


if len(commands) == 1:
    commands = re.split(r"\n(?=ALTER|DROP|CREATE)", rollback_sql, flags=re.IGNORECASE)
    commands = [cmd.strip() for cmd in commands if cmd.strip()]

commands = normalize_rollback_command_order(commands)

# Final formatting for Databricks notebook
formatted_sql = "\n\n-- COMMAND ----------\n\n".join(
    [cmd.rstrip(";") + ";" for cmd in commands]
)

# ----------------------------------------
# Write rollback.sql
# ----------------------------------------

with open("rollback.sql", "w") as f:
    f.write(formatted_sql)

print("Rollback SQL generated successfully ")
