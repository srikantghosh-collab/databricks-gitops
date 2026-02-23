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

You must generate a rollback SQL script for the given DDL.

STRICT RULES (NON-NEGOTIABLE):

1. You MUST start output with exactly one of:
   -- ROLLBACK_TYPE: REVERSIBLE
   -- ROLLBACK_TYPE: PARTIAL
   -- ROLLBACK_TYPE: IRREVERSIBLE

2. Output ONLY SQL statements and SQL comments (--).
   No markdown. No JSON. No explanations outside comments.

3. NEVER hallucinate previous values.
   If previous state is UNKNOWN, rollback must be PARTIAL or IRREVERSIBLE.

4. If rollback is unsafe:
   - DO NOT generate executable SQL.
   - ONLY provide SQL comments with concrete recovery steps.

5. Assume production Databricks Delta Lake environment.

--------------------------------------------------
DDL RULES
--------------------------------------------------

CREATE TABLE
Rollback: DROP TABLE table_name;

DROP TABLE
IRREVERSIBLE
Recovery:
-- Restore from DEEP CLONE backup or Delta Time Travel

ALTER TABLE ADD COLUMN
REVERSIBLE
Rollback: ALTER TABLE DROP COLUMN

ALTER TABLE DROP COLUMN
IRREVERSIBLE

ALTER TABLE SET TBLPROPERTIES
PARTIAL
- If previous value known → restore old value
- If unknown → comments only

--------------------------------------------------
"""

# ----------------------------------------
# Helpers
# ----------------------------------------
def format_previous_state(item):
    prev = item.get("previous_state")
    if not prev:
        return "UNKNOWN"
    return json.dumps(prev, indent=2)


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
    # SAFETY CHECK: NO HALLUCINATION
    # ------------------------------------
    if (
        "SET TBLPROPERTIES" in rollback_sql.upper()
        and previous_state == "UNKNOWN"
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