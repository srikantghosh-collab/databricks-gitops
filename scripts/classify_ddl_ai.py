import os
import json
from openai import AzureOpenAI

print("Starting AI DDL Classification...")

DDL_ARTIFACT = "ddl_output.json"

# --------------------------------
# Load DDL artifact
# --------------------------------

if not os.path.exists(DDL_ARTIFACT):
    print("No ddl_output.json found — skipping classification")
    print("##vso[task.setvariable variable=IS_DROP;isOutput=true]false")
    print("##vso[task.setvariable variable=ROLLBACK_TYPE;isOutput=true]NONE")
    exit(0)

with open(DDL_ARTIFACT) as f:
    payload = json.load(f)

ddls = payload.get("ddls", [])

if not ddls:
    print("No DDL statements found")
    print("##vso[task.setvariable variable=IS_DROP;isOutput=true]false")
    print("##vso[task.setvariable variable=ROLLBACK_TYPE;isOutput=true]NONE")
    exit(0)

# --------------------------------
# Prepare AI input
# --------------------------------

ddl_statements = "\n".join(d["statement"] for d in ddls)

system_prompt = """
You are a Databricks Delta Lake DDL expert.

Classify the given DDL statements.

Return ONLY ONE of the following classifications:

CREATE_TABLE
ALTER_TABLE
DROP_TABLE

Rules:

CREATE TABLE → CREATE_TABLE

ALTER TABLE → ALTER_TABLE

DROP TABLE → DROP_TABLE

Return ONLY the classification name.
No explanation.
"""

user_prompt = f"""
Classify the following DDL statements:

{ddl_statements}
"""

# --------------------------------
# Call Azure OpenAI
# --------------------------------

client = AzureOpenAI(
    api_key=os.environ["AZURE_OPENAI_KEY"],
    azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
    api_version="2024-02-15-preview"
)

response = client.chat.completions.create(
    model=os.environ["AZURE_DEPLOYMENT_NAME"],
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ],
    temperature=0
)

ai_class = response.choices[0].message.content.strip().upper()

print("AI classification:", ai_class)

VALID_CLASSES = {
    "CREATE_TABLE",
    "ALTER_TABLE",
    "DROP_TABLE"
}

if ai_class not in VALID_CLASSES:
    print("Invalid AI classification — defaulting to ALTER_TABLE")
    ai_class = "ALTER_TABLE"

# --------------------------------
# Derive pipeline behavior
# --------------------------------

if ai_class == "DROP_TABLE":
    is_drop = True
    rollback_type = "AI_RECONSTRUCT"

elif ai_class in ("CREATE_TABLE", "ALTER_TABLE"):
    is_drop = False
    rollback_type = "AI_RECONSTRUCT"

else:
    is_drop = False
    rollback_type = "NONE"

# --------------------------------
# Final logs
# --------------------------------

print("Final Classification:", ai_class)
print("Rollback Type:", rollback_type)
print("Is Drop:", is_drop)

# --------------------------------
# Azure DevOps output variables
# --------------------------------

is_drop_str = str(is_drop).lower()

print(f"##vso[task.setvariable variable=IS_DROP;isOutput=true]{is_drop_str}")
print(f"##vso[task.setvariable variable=ROLLBACK_TYPE;isOutput=true]{rollback_type}")