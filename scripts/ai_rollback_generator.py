import json
import os
from openai import AzureOpenAI

DDL_ARTIFACT = "ddl_output.json"

if not os.path.exists(DDL_ARTIFACT):
    print("DDL artifact not found")
    exit(0)

with open(DDL_ARTIFACT) as f:
    payload = json.load(f)

ddls = payload.get("ddls", [])
commit_id = payload.get("commit_id")

if not ddls:
    print("No DDL statements found")
    exit(0)

# Azure OpenAI client
client = AzureOpenAI(
    api_key=os.environ["AZURE_OPENAI_KEY"],
    api_version="2024-02-15-preview",
    azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
)


SYSTEM_PROMPT = """
You are a senior Databricks Delta Lake schema governance and migration expert.

Your task:
Generate SAFE and deterministic rollback SQL for the given forward DDL.

STRICT OUTPUT RULES:
1. Output ONLY SQL.
2. Never output JSON.
3. Never output markdown.
4. Never explain outside SQL comments.
5. Rollback must be executable when deterministic.
6. Never guess previous schema or property values.

---------------------------------------
DETERMINISTIC RULES (MUST FOLLOW)
---------------------------------------

1. CREATE TABLE
→ Generate:
DROP TABLE IF EXISTS <table_name>;

2. ALTER TABLE ADD COLUMN
→ Generate:
ALTER TABLE <table_name> DROP COLUMN <column_name>;

3. ALTER TABLE RENAME COLUMN
→ Generate reverse rename.

---------------------------------------
DATATYPE CHANGE (SAFE MIGRATION PATTERN)
---------------------------------------

If forward DDL changes column datatype (CHANGE COLUMN / ALTER COLUMN):

DO NOT mark unsupported.

Generate SAFE MIGRATION SQL using this pattern:

-- SAFE COLUMN TYPE MIGRATION
ALTER TABLE <table> ADD COLUMN <column>_new <new_type>;

UPDATE <table>
SET <column>_new = <column>;

ALTER TABLE <table> DROP COLUMN <column>;

ALTER TABLE <table> RENAME COLUMN <column>_new TO <column>;

---------------------------------------
SET TBLPROPERTIES (SNAPSHOT-AWARE LOGIC)
---------------------------------------

If forward DDL is ALTER TABLE SET TBLPROPERTIES:

You will receive additional context:

SNAPSHOT_SQL:
- If provided, it contains executable SQL that restores previous properties.
- If empty or null, this means properties were not previously set.

Rules:

1. If SNAPSHOT_SQL is provided:
   Output SNAPSHOT_SQL exactly as rollback SQL.

2. If SNAPSHOT_SQL is empty:
   Generate:
   ALTER TABLE <table_name>
   UNSET TBLPROPERTIES (<property_list>);

3. Never assume previous values.
4. Never invent property values.

---------------------------------------
UNSUPPORTED CASES
---------------------------------------

If rollback is unsafe and no snapshot exists:

Return SQL comments only:

-- UNSUPPORTED AUTOMATIC ROLLBACK
-- Reason: Previous state cannot be deterministically restored
-- MANUAL INTERVENTION REQUIRED

---------------------------------------
GUARDRAILS
---------------------------------------

- Never fabricate previous values.
- Never assume schema history.
- Prefer safe migration over rejection.
- Rollback must preserve data integrity.


"""

def generate_rollback(forward_sql):
    response = client.chat.completions.create(
        model=os.environ["AZURE_DEPLOYMENT_NAME"],
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Forward DDL:\n{forward_sql}"}
        ],
        temperature=0
    )

    return response.choices[0].message.content.strip()

rollback_lines = []
rollback_lines.append(f"-- Rollback script for commit: {commit_id}\n")

for item in ddls:
    forward_sql = item["statement"]
    rollback_sql = generate_rollback(forward_sql)

    rollback_lines.append(f"-- Forward DDL:")
    rollback_lines.append(f"-- {forward_sql}")
    rollback_lines.append(rollback_sql)
    rollback_lines.append("")

rollback_filename = os.path.join(
    os.environ.get("SYSTEM_DEFAULTWORKINGDIRECTORY", "."),
    f"rollback_{commit_id}.sql"
)


with open(rollback_filename, "w") as f:
    f.write("\n".join(rollback_lines))

print(f"Rollback SQL generated: {rollback_filename}")
