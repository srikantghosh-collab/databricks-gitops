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
You are a Databricks Delta Lake expert.

Generate SAFE rollback SQL for the given forward DDL.

Rules:
- Always return valid SQL or SQL comments.
- Never return JSON.
- If rollback is unsupported or unsafe, return only SQL comments.
- Comments must explain:
  1. Why rollback is unsupported
  2. Suggested manual steps
- Do not add markdown.
- Do not explain outside SQL comments.
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

rollback_filename = f"rollback_{commit_id}.sql"

with open(rollback_filename, "w") as f:
    f.write("\n".join(rollback_lines))

print(f"Rollback SQL generated: {rollback_filename}")
