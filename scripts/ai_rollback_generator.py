import json
import os
import sys
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
# SYSTEM PROMPT (STRICT)
# ----------------------------------------
SYSTEM_PROMPT = """
You are an expert Databricks Delta Lake database reliability engineer.

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

--------------------------------------------------

DROP TABLE
Rollback:
-- ROLLBACK NOT POSSIBLE

--------------------------------------------------

ALTER TABLE ADD COLUMN column_name TYPE
Rollback:
ALTER TABLE table_name DROP COLUMN column_name;

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
-- ROLLBACK NOT POSSIBLE

--------------------------------------------------

ALTER TABLE ALTER COLUMN column_name SET NOT NULL
Rollback:
ALTER TABLE table_name ALTER COLUMN column_name DROP NOT NULL;

--------------------------------------------------

ALTER TABLE ALTER COLUMN column_name DROP NOT NULL
Rollback:
ALTER TABLE table_name ALTER COLUMN column_name SET NOT NULL;

--------------------------------------------------

ALTER TABLE ALTER COLUMN column_name SET DEFAULT value
Rollback:
ALTER TABLE table_name ALTER COLUMN column_name DROP DEFAULT;

--------------------------------------------------

ALTER TABLE ALTER COLUMN column_name DROP DEFAULT
Rollback:
-- ROLLBACK NOT POSSIBLE

--------------------------------------------------

ALTER TABLE ALTER COLUMN column_name TYPE new_type
Rollback:
-- ROLLBACK NOT POSSIBLE

--------------------------------------------------

ALTER TABLE ALTER COLUMN column_name COMMENT 'text'
Rollback:
-- ROLLBACK NOT POSSIBLE

--------------------------------------------------

ALTER TABLE SET TBLPROPERTIES ('key'='value')
Rollback:
ALTER TABLE table_name UNSET TBLPROPERTIES ('key');

--------------------------------------------------

ALTER TABLE UNSET TBLPROPERTIES ('key')
Rollback:
-- ROLLBACK NOT POSSIBLE

--------------------------------------------------

ALTER TABLE RENAME TO new_table
Rollback:
ALTER TABLE new_table RENAME TO old_table;

--------------------------------------------------

ALTER TABLE REPLACE COLUMNS (...)
Rollback:
-- ROLLBACK NOT POSSIBLE

--------------------------------------------------

ALTER TABLE CLUSTER BY (...)
Rollback:
-- ROLLBACK NOT POSSIBLE

--------------------------------------------------

ALTER TABLE SET LOCATION
Rollback:
-- ROLLBACK NOT POSSIBLE

--------------------------------------------------

ALTER TABLE SET OWNER
Rollback:
-- ROLLBACK NOT POSSIBLE

--------------------------------------------------

ALTER TABLE ADD CONSTRAINT constraint_name
Rollback:
ALTER TABLE table_name DROP CONSTRAINT constraint_name;

--------------------------------------------------

ALTER TABLE DROP CONSTRAINT constraint_name
Rollback:
-- ROLLBACK NOT POSSIBLE

--------------------------------------------------

ALTER TABLE ENABLE CHANGE DATA FEED
Rollback:
ALTER TABLE table_name SET TBLPROPERTIES ('delta.enableChangeDataFeed'='false');

--------------------------------------------------

ALTER TABLE SET COMMENT
Rollback:
-- ROLLBACK NOT POSSIBLE

--------------------------------------------------

Return ONLY the rollback SQL statements in reverse order."""
# ----------------------------------------
# Helpers
# ----------------------------------------
def format_previous_state(item):
    prev = item.get("previous_state")
    if not prev:
        return "UNKNOWN"
    return json.dumps(prev, indent=2)


def table_created_in_same_commit(ddls, current_item):
    """
    Returns True if the table of current_item
    was created earlier in the same commit.
    """
    stmt = current_item["statement"].upper()

    # extract table name roughly
    tokens = stmt.split()
    table_name = None
    if "TABLE" in tokens:
        idx = tokens.index("TABLE")
        if idx + 1 < len(tokens):
            table_name = tokens[idx + 1]

    if not table_name:
        return False

    for d in ddls:
        if d is current_item:
            break
        if d["statement"].upper().startswith("CREATE TABLE") and table_name in d["statement"].upper():
            return True

    return False


def generate_rollback(forward_sql, previous_state):
    response = client.chat.completions.create(
        model=os.environ["AZURE_DEPLOYMENT_NAME"],
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"""
Forward DDL:
{forward_sql}

Previous Table State:
{previous_state}
"""
            }
        ],
        temperature=0
    )

    return response.choices[0].message.content.strip()


# ----------------------------------------
# Generate rollback SQL
# ----------------------------------------
rollback_lines = []
rollback_lines.append(f"-- Rollback script for commit: {commit_id}")
rollback_lines.append("")

for item in ddls:
    ddl_id = item.get("id")
    forward_sql = item["statement"]
    previous_state = format_previous_state(item)

    rollback_sql = generate_rollback(forward_sql, previous_state)

    # ------------------------------------
    # SAFETY CHECK (FIXED)
    # ------------------------------------
    if (
        "SET TBLPROPERTIES" in rollback_sql.upper()
        and previous_state == "UNKNOWN"
        and not table_created_in_same_commit(ddls, item)
    ):
        print("ERROR: Unsafe rollback generated without previous state.")
        print(f"DDL: {forward_sql}")
        sys.exit(1)

    rollback_lines.append("-- ========================================")
    rollback_lines.append(f"-- DDL_ID: {ddl_id}")
    rollback_lines.append("-- Forward DDL:")
    rollback_lines.append(f"-- {forward_sql}")
    rollback_lines.append("-- ========================================")
    rollback_lines.append(rollback_sql)
    rollback_lines.append("")

# ----------------------------------------
# Write rollback file
# ----------------------------------------
rollback_filename = os.path.join(
    os.environ.get("SYSTEM_DEFAULTWORKINGDIRECTORY", "."),
    "rollback.sql"
)

with open(rollback_filename, "w") as f:
    f.write("\n".join(rollback_lines))

print(f"Rollback SQL generated: {rollback_filename}")