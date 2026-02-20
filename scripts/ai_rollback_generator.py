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
You are a senior Databricks Delta Lake schema governance expert.

Your task:
Generate a SAFE rollback SQL statement for the given forward DDL.

STRICT RULES:

1. Always return valid SQL.
2. Never return JSON.
3. Never return markdown.
4. Never explain outside SQL.
5. Output must be either:
   - Executable rollback SQL (for deterministic operations)
   OR
   - SQL comments explaining why rollback is unsupported.

DETERMINISTIC RULES (MUST FOLLOW):

- CREATE TABLE → generate:
  DROP TABLE IF EXISTS <table_name>;

- ALTER TABLE ADD COLUMN → generate:
  ALTER TABLE <table_name> DROP COLUMN <column_name>;

- ALTER TABLE RENAME COLUMN → generate reverse rename.

- DROP TABLE → assume restore from backup (use SQL comment only).

NON-DETERMINISTIC / UNSUPPORTED CASES:

If rollback is unsafe or the previous state is unknown, return ONLY SQL comments in this format:

-- UNSUPPORTED ALTER DETECTED
-- Reason: <clear technical reason>
-- MANUAL INTERVENTION REQUIRED
-- Suggested steps:
-- 1. ...
-- 2. ...

Never guess previous values.
Never invent schema.
Never assume previous property values.

Assume Delta Lake limitations:
- Data type change is not safely reversible.
- SET TBLPROPERTIES may not have known previous state.
- Protocol upgrades cannot be downgraded.

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
