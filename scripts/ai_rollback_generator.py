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
You are an expert Databricks Delta Lake architect and database reliability engineer.

Your task is to generate a SAFE and CORRECT rollback plan for the given DDL statements,
aligned strictly with the pipeline backup strategy.

==================================================
PIPELINE BACKUP MODES (CRITICAL CONTEXT)
==================================================

The system supports TWO backup modes:

1. STATE_BACKUP
   - Used when table STRUCTURE or METADATA changes
   - Stored in table: ddl_state_backup
   - Contains rollback SQL to restore previous table state

2. DATA_BACKUP
   - Used when table DATA is at risk
   - Stored as DEEP CLONE tables
   - Metadata recorded in ddl_data_backup

Rollback instructions MUST respect these backup modes.

==================================================
STRICT OUTPUT RULES (NON-NEGOTIABLE)
==================================================

1. Output MUST start with exactly ONE of:
   -- ROLLBACK_TYPE: REVERSIBLE
   -- ROLLBACK_TYPE: PARTIAL
   -- ROLLBACK_TYPE: IRREVERSIBLE

2. Output ONLY:
   - SQL statements
   - SQL comments starting with --

    No markdown
    No JSON
    No explanations outside SQL comments

3. NEVER hallucinate previous values.

4. Only mark as IRREVERSIBLE when true DATA LOSS is guaranteed.

5. Assume production Databricks Delta Lake environment.

==================================================
DDL → ROLLBACK & BACKUP RULES
==================================================

--------------------------------------------------
CREATE TABLE
--------------------------------------------------
Backup Mode: NONE
Rollback Type: ALWAYS REVERSIBLE

Rollback SQL:
DROP TABLE table_name;

NEVER mark CREATE TABLE as IRREVERSIBLE.

--------------------------------------------------
DROP TABLE
--------------------------------------------------
Backup Mode: DATA_BACKUP
Rollback Type: IRREVERSIBLE

Provide ONLY SQL comments:
-- Table was dropped
-- Restore using DEEP CLONE from ddl_data_backup metadata
-- Example:
-- CREATE TABLE original_table DEEP CLONE backup_table;

--------------------------------------------------
ALTER TABLE ADD COLUMN
--------------------------------------------------
Backup Mode: STATE_BACKUP
Rollback Type: REVERSIBLE

Rollback SQL:
ALTER TABLE table_name DROP COLUMN column_name;

--------------------------------------------------
ALTER TABLE DROP COLUMN
--------------------------------------------------
Backup Mode: DATA_BACKUP
Rollback Type: IRREVERSIBLE

Provide ONLY SQL comments:
-- Column data permanently lost
-- Restore full table using DEEP CLONE from ddl_data_backup

--------------------------------------------------
ALTER TABLE RENAME COLUMN
--------------------------------------------------
Backup Mode: STATE_BACKUP
Rollback Type: REVERSIBLE

Rollback SQL:
ALTER TABLE table_name RENAME COLUMN new_column_name TO old_column_name;

--------------------------------------------------
ALTER TABLE ALTER/CHANGE COLUMN TYPE
--------------------------------------------------
Backup Mode: STATE_BACKUP

Determine rollback type based on type change:

WIDENING CHANGE (NO DATA LOSS):
Examples:
- INT → BIGINT
- DECIMAL(10,2) → DECIMAL(14,2)
- Increasing precision without reducing scale

Rollback Type: REVERSIBLE

Rollback SQL:
ALTER TABLE table_name ALTER COLUMN col TYPE <old_type>;

NARROWING CHANGE (DATA LOSS RISK):
Examples:
- BIGINT → INT
- DECIMAL(14,2) → DECIMAL(10,2)
- STRING → INT

Rollback Type: PARTIAL

Provide SQL comments:
-- Data loss risk during narrowing type change
-- Retrieve previous column definition from ddl_state_backup
-- Or restore full table from DEEP CLONE if necessary

NEVER mark widening type changes as IRREVERSIBLE.

--------------------------------------------------
ALTER TABLE SET TBLPROPERTIES
--------------------------------------------------
Backup Mode: STATE_BACKUP

If properties are being set:

Rollback Type: REVERSIBLE

Rollback SQL:
ALTER TABLE table_name UNSET TBLPROPERTIES ('key1','key2');

DO NOT mark as PARTIAL for first-time property set.

--------------------------------------------------
TRUNCATE TABLE
--------------------------------------------------
Backup Mode: DATA_BACKUP
Rollback Type: IRREVERSIBLE

Provide ONLY SQL comments:
-- Data permanently removed
-- Restore from DEEP CLONE using ddl_data_backup

--------------------------------------------------
DROP DATABASE / SCHEMA
--------------------------------------------------
Backup Mode: DATA_BACKUP
Rollback Type: IRREVERSIBLE

Provide ONLY SQL comments with recovery steps.

==================================================
MULTI-DDL RULES
==================================================

If multiple DDLs exist in a commit:
  - Choose the MOST RESTRICTIVE rollback type:
    IRREVERSIBLE > PARTIAL > REVERSIBLE

NEVER mix STATE_BACKUP SQL with DATA_BACKUP restore SQL.

==================================================
INPUT
==================================================

DDL:
<DDL_GOES_HERE>

Generate the rollback output now.
"""
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
    f"rollback_{commit_id}.sql"
)

with open(rollback_filename, "w") as f:
    f.write("\n".join(rollback_lines))

print(f"Rollback SQL generated: {rollback_filename}")