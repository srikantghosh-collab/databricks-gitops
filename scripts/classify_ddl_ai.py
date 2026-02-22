import os
import json
from openai import AzureOpenAI

print("Starting AI DDL Classification...")

# -----------------------------
# Load DDL artifact
# -----------------------------
if not os.path.exists("ddl_output.json"):
    print("No ddl_output.json found — skipping classification")
    print("##vso[task.setvariable variable=IS_DROP;isOutput=true]false")
    print("##vso[task.setvariable variable=ROLLBACK_TYPE;isOutput=true]NONE")
    exit(0)

with open("ddl_output.json") as f:
    payload = json.load(f)

ddls = payload.get("ddls", [])

if not ddls:
    print("No DDL statements found")
    print("##vso[task.setvariable variable=IS_DROP;isOutput=true]false")
    print("##vso[task.setvariable variable=ROLLBACK_TYPE;isOutput=true]NONE")
    exit(0)

# -----------------------------
# Prepare AI Input
# -----------------------------
ddl_statements = "\n".join([d["statement"] for d in ddls])

system_prompt = """
You are a Databricks Delta Lake DDL expert.

You may return MULTIPLE comma-separated classifications if the DDL contains
more than one type of operation.

Valid classifications:
DROP_TABLE
TRUNCATE_TABLE
DESTRUCTIVE_ALTER
CREATE_TABLE
SET_TBLPROPERTIES
SAFE_ALTER

Return ONLY the classification names, comma-separated if multiple.
"""

user_prompt = f"""
Classify the following DDL statements:

{ddl_statements}
"""

# -----------------------------
# Call Azure OpenAI
# -----------------------------
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

ai_raw = response.choices[0].message.content.strip().upper()
print(f"AI raw classification: {ai_raw}")

# -----------------------------
# Parse multiple labels
# -----------------------------
ai_labels = [x.strip() for x in ai_raw.replace("\n", "").split(",") if x.strip()]

VALID_CLASSES = {
    "DROP_TABLE",
    "TRUNCATE_TABLE",
    "DESTRUCTIVE_ALTER",
    "CREATE_TABLE",
    "SET_TBLPROPERTIES",
    "SAFE_ALTER"
}

ai_labels = [x for x in ai_labels if x in VALID_CLASSES]

if not ai_labels:
    print("AI returned no valid classification. Defaulting to SAFE_ALTER.")
    ai_labels = ["SAFE_ALTER"]

# -----------------------------
# PRIORITY DECISION (CRITICAL FIX)
# -----------------------------
PRIORITY_ORDER = [
    "DROP_TABLE",
    "TRUNCATE_TABLE",
    "DESTRUCTIVE_ALTER",
    "CREATE_TABLE",
    "SET_TBLPROPERTIES",
    "SAFE_ALTER"
]

final_classification = "SAFE_ALTER"
for p in PRIORITY_ORDER:
    if p in ai_labels:
        final_classification = p
        break

# -----------------------------
# Determine IS_DROP
# -----------------------------
is_drop = final_classification in [
    "DROP_TABLE",
    "TRUNCATE_TABLE",
    "DESTRUCTIVE_ALTER"
]

# -----------------------------
# Determine ROLLBACK_TYPE
# -----------------------------
if final_classification in [
    "DROP_TABLE",
    "TRUNCATE_TABLE",
    "DESTRUCTIVE_ALTER",
    "CREATE_TABLE"
]:
    rollback_type = "TABLE"

elif final_classification == "SET_TBLPROPERTIES":
    rollback_type = "TBLPROPERTIES"

else:
    rollback_type = "NONE"

# -----------------------------
# Final logs (VERY IMPORTANT)
# -----------------------------
print("Resolved AI labels:", ai_labels)
print("Final Classification:", final_classification)
print("Rollback Type:", rollback_type)
print("Is Drop:", is_drop)

# -----------------------------
# Azure DevOps Output Variables
# -----------------------------
print(f"##vso[task.setvariable variable=IS_DROP;isOutput=true]{str(is_drop).lower()}")
print(f"##vso[task.setvariable variable=ROLLBACK_TYPE;isOutput=true]{rollback_type}")