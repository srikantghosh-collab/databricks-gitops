import os
import json
from openai import AzureOpenAI

print("Starting AI DDL Classification...")

# -----------------------------
# Load DDL artifact
# -----------------------------
if not os.path.exists("ddl_output.json"):
    print("No ddl_output.json found — skipping classification")
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

Classify the DDL into one of these categories:

1. DROP_TABLE
2. TRUNCATE_TABLE
3. DESTRUCTIVE_ALTER
4. SET_TBLPROPERTIES
5. SAFE_ALTER
6. CREATE_TABLE

Return ONLY the category name.
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

ai_response = response.choices[0].message.content.strip().upper()

print(f"AI raw classification: {ai_response}")

# -----------------------------
# Normalize classification
# -----------------------------
valid_classes = [
    "DROP_TABLE",
    "TRUNCATE_TABLE",
    "DESTRUCTIVE_ALTER",
    "SET_TBLPROPERTIES",
    "SAFE_ALTER",
    "CREATE_TABLE"
]

if ai_response not in valid_classes:
    print("AI returned unexpected classification. Defaulting to SAFE_ALTER.")
    ai_response = "SAFE_ALTER"

# -----------------------------
# Determine IS_DROP
# -----------------------------
is_drop = ai_response in [
    "DROP_TABLE",
    "TRUNCATE_TABLE",
    "DESTRUCTIVE_ALTER"
]

# -----------------------------
# Determine ROLLBACK_TYPE
# -----------------------------
if ai_response in ["DROP_TABLE", "TRUNCATE_TABLE", "DESTRUCTIVE_ALTER", "CREATE_TABLE"]:
    rollback_type = "TABLE"
elif ai_response == "SET_TBLPROPERTIES":
    rollback_type = "TBLPROPERTIES"
else:
    rollback_type = "NONE"

print(f"Final Classification: {ai_response}")
print(f"Rollback Type: {rollback_type}")
print(f"Is Drop: {is_drop}")

# -----------------------------
# 🔥 Azure DevOps Output Variables (CRITICAL)
# -----------------------------
print(f"##vso[task.setvariable variable=IS_DROP;isOutput=true]{str(is_drop).lower()}")
print(f"##vso[task.setvariable variable=ROLLBACK_TYPE;isOutput=true]{rollback_type}")