import json
import os
import sys
import re
from openai import AzureOpenAI

DDL_ARTIFACT = "ddl_output.json"

if not os.path.exists(DDL_ARTIFACT):
    print("DDL artifact not found")
    sys.exit(0)

with open(DDL_ARTIFACT) as f:
    payload = json.load(f)

ddls = payload.get("ddls", [])
commit_id = payload.get("commit_id")

if not ddls:
    print("No DDL statements found")
    sys.exit(0)

# ----------------------------------------
# Azure OpenAI client
# ----------------------------------------
client = AzureOpenAI(
    api_key=os.environ["AZURE_OPENAI_KEY"],
    api_version="2024-02-15-preview",
    azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
)

# ----------------------------------------
# SYSTEM PROMPT (UNCHANGED)
# ----------------------------------------
SYSTEM_PROMPT = """You are an expert Databricks Delta Lake database reliability engineer.

Your task is to generate ONLY the rollback SQL for the given DDL statements.

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
8. If rollback is impossible output exactly:
   -- ROLLBACK NOT POSSIBLE

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
-- ROLLBACK NOT POSSIBLE

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
-- ROLLBACK NOT POSSIBLE

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
-- ROLLBACK NOT POSSIBLE

ALTER TABLE ALTER COLUMN column_name TYPE new_type
Rollback:
-- ROLLBACK NOT POSSIBLE

ALTER TABLE ALTER COLUMN column_name COMMENT 'text'
Rollback:
-- ROLLBACK NOT POSSIBLE

ALTER TABLE SET TBLPROPERTIES ('key'='value')
Rollback:
ALTER TABLE table_name UNSET TBLPROPERTIES ('key');

ALTER TABLE UNSET TBLPROPERTIES ('key')
Rollback:
-- ROLLBACK NOT POSSIBLE

ALTER TABLE RENAME TO new_table
Rollback:
ALTER TABLE new_table RENAME TO old_table;

ALTER TABLE REPLACE COLUMNS (...)
Rollback:
-- ROLLBACK NOT POSSIBLE

ALTER TABLE CLUSTER BY (...)
Rollback:
-- ROLLBACK NOT POSSIBLE

ALTER TABLE SET LOCATION
Rollback:
-- ROLLBACK NOT POSSIBLE

ALTER TABLE SET OWNER
Rollback:
-- ROLLBACK NOT POSSIBLE

ALTER TABLE ADD CONSTRAINT constraint_name
Rollback:
ALTER TABLE table_name DROP CONSTRAINT constraint_name;

ALTER TABLE DROP CONSTRAINT constraint_name
Rollback:
-- ROLLBACK NOT POSSIBLE

ALTER TABLE ENABLE CHANGE DATA FEED
Rollback:
ALTER TABLE table_name SET TBLPROPERTIES ('delta.enableChangeDataFeed'='false');

ALTER TABLE SET COMMENT
Rollback:
-- ROLLBACK NOT POSSIBLE

Return ONLY the rollback SQL statements in reverse order.
"""

# ----------------------------------------
# Prepare forward DDL batch
# ----------------------------------------
forward_sql_list = []
previous_state_list = []

for i, item in enumerate(ddls, start=1):
    stmt = item["statement"]
    prev_state = item.get("previous_state")

    forward_sql_list.append(stmt)

    previous_state_list.append({
        "statement": stmt,
        "previous_state": prev_state
    })

forward_sql_text = "\n".join(forward_sql_list)
previous_state_text = json.dumps(previous_state_list, indent=2)

# ----------------------------------------
# Special handling for CREATE TABLE
# ----------------------------------------

first_stmt = ddls[0]["statement"].upper()


create_match = re.search(
    r"CREATE\s+TABLE\s+(IF\s+NOT\s+EXISTS\s+)?([a-zA-Z0-9_.]+)",
    first_stmt,
    re.IGNORECASE
)

if create_match:

    table_name = create_match.group(2)

    # safest rollback
    rollback_sql = f"DROP TABLE IF EXISTS {table_name};"

else:

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

Previous table state before the commit:

{previous_state_text}

Generate rollback SQL.
Remember rollback must be in reverse order.
"""
            }
        ]
    )

    rollback_sql = response.choices[0].message.content.strip()

# ----------------------------------------
# Safety check
# ----------------------------------------

if "CREATE TABLE" in rollback_sql.upper():
    print("ERROR: Unsafe rollback detected.")
    sys.exit(1)

# ----------------------------------------
# Convert to notebook cells
# ----------------------------------------

commands = [
    cmd.strip()
    for cmd in rollback_sql.split(";")
    if cmd.strip() and not cmd.strip().startswith("--")
]

formatted_sql = "\n\n-- COMMAND ----------\n\n".join([c + ";" for c in commands])

# ----------------------------------------
# Write rollback.sql
# ----------------------------------------

rollback_filename = os.path.join(
    os.environ.get("SYSTEM_DEFAULTWORKINGDIRECTORY", "."),
    "rollback.sql"
)

with open(rollback_filename, "w") as f:
    f.write(formatted_sql)

print("Rollback SQL generated:", rollback_filename)