import json
import os
import sys
from openai import AzureOpenAI


print("🔵 AI Classification Stage Starting...")

# Step 1: Load detected DDL
if not os.path.exists("ddl_output.json"):
    print("No ddl_output.json found — skipping AI classification")
    sys.exit(0)

with open("ddl_output.json", "r") as f:
    data = json.load(f)

ddl = data.get("ddl")

if not ddl:
    print("No DDL found — skipping AI classification")
    sys.exit(0)

ddl = ddl.strip()


if not ddl:
    print("No DDL found")
    sys.exit(0)

print("DDL to classify:", ddl)

client = AzureOpenAI(
    api_key=os.environ["AZURE_OPENAI_KEY"],
    azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
    api_version="2024-02-15-preview"
)

prompt = f"""
You are a SQL safety analyzer.

Classify this DDL statement:

{ddl}

Return ONLY JSON:

{{ "classification": "reversible" }}
or
{{ "classification": "irreversible" }}
"""

try:
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )

    result = json.loads(response.choices[0].message.content)
    classification = result["classification"]

except Exception as e:
    print("AI failed — using fallback rule")
    print("Error:", e)

    classification = (
        "irreversible"
        if ddl.upper().startswith("DROP")
        else "reversible"
    )

classification = result["classification"].strip().lower()
print("AI classification:", classification)

is_drop = classification == "irreversible"
print("FINAL IS_DROP VALUE:", is_drop)

# Pipeline variable
sys.stdout.flush()
print(f"##vso[task.setvariable variable=IS_DROP;isOutput=true]{str(is_drop).lower()}")
sys.stdout.flush()

print("🔵 AI Classification Complete")
