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
You are an expert Databricks Delta Lake architect and database reliability engineer.

Your task is to analyze given Databricks Delta Lake DDL statements and generate
a rollback SQL script in PURE SQL format.

You must strictly follow these rules:

1. First classify each DDL as:
   - REVERSIBLE
   - IRREVERSIBLE
   - PARTIALLY_REVERSIBLE

2. If the DDL is REVERSIBLE:
   - Generate the exact rollback SQL that safely reverts the change.
   - Output ONLY valid SQL statements (no JSON, no markdown).

3. If the DDL is PARTIALLY_REVERSIBLE:
   - Generate rollback SQL where possible.
   - For the unsafe portion, add SQL comments explaining:
     - Why rollback is unsafe
     - What manual steps are required

4. If the DDL is IRREVERSIBLE:
   - DO NOT generate fake rollback SQL.
   - Instead, generate ONLY SQL comments with:
     - Reason rollback is unsafe
     - Exact suggested manual recovery steps

5. Suggested steps MUST be concrete and actionable.
   Do NOT write vague text like "manual intervention required".

6. Use SQL comments format ONLY:
   -- like this

7. Never output explanations outside SQL comments.
8. Never output JSON.
9. Never hallucinate previous schema values.
10. Assume production Databricks Delta Lake environment.

--------------------------------------------------
ROLLBACK RULES BY DDL TYPE
--------------------------------------------------

CREATE TABLE
Rollback: DROP TABLE table_name;

DROP TABLE
Unsafe
Suggested steps:
  - Restore from last backup OR Delta Time Travel if available

TRUNCATE TABLE
Unsafe
Suggested steps:
  - Restore table from backup snapshot

ALTER TABLE ADD COLUMN
Reversible
Rollback: ALTER TABLE DROP COLUMN

ALTER TABLE DROP COLUMN
Unsafe
Suggested steps:
  - Restore from backup OR recreate column and reload data

ALTER TABLE RENAME COLUMN
Reversible (if column mapping enabled)
Rollback: rename column back

ALTER TABLE CHANGE / ALTER COLUMN DATA TYPE
Unsafe
Suggested steps:
  1. Create a new column with old data type
  2. Backfill data if possible
  3. Drop modified column
  4. Rename new column

ALTER TABLE SET TBLPROPERTIES
PARTIALLY_REVERSIBLE
If previous values are known:
  - Rollback: SET TBLPROPERTIES to previous values
If previous values are unknown:
  - Rollback: UNSET modified properties
Always include suggested steps explaining property history handling

ALTER TABLE UNSET TBLPROPERTIES
PARTIALLY_REVERSIBLE
Suggested steps:
  - Reapply previous property values manually if required

ALTER TABLE ADD CONSTRAINT
Reversible
Rollback: DROP CONSTRAINT

ALTER TABLE DROP CONSTRAINT
Unsafe
Suggested steps:
  - Recreate constraint using original definition

ALTER TABLE SET NOT NULL
Reversible
Rollback: DROP NOT NULL

ALTER TABLE DROP NOT NULL
Reversible
Rollback: SET NOT NULL

--------------------------------------------------
OUTPUT FORMAT EXAMPLE
--------------------------------------------------

-- Forward DDL:
-- ALTER TABLE employee ALTER COLUMN salary TYPE INT

-- Rollback is UNSAFE.
-- Reason:
-- Changing column data type can permanently corrupt existing data.

-- Suggested manual recovery steps:
-- 1. Create a new column with the previous data type.
-- 2. Backfill data from backups or Delta Time Travel.
-- 3. Drop the modified column.
-- 4. Rename the restored column to original name.

--------------------------------------------------
IMPORTANT
--------------------------------------------------
Output ONLY SQL and SQL comments
No markdown
No JSON
No explanations outside comments


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
