import json
import os
import sys
from openai import AzureOpenAI

print("🤖 AI DDL Classification Started")

if not os.path.exists("ddl_output.json"):
    print("No ddl_output.json found")
    sys.exit(0)

with open("ddl_output.json") as f:
    data = json.load(f)

ddls = data.get("ddls", [])

if not ddls:
    print("No DDLs to classify")
    sys.exit(0)

client = AzureOpenAI(
    api_key=os.environ["AZURE_OPENAI_KEY"],
    azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
    api_version="2024-02-15-preview"
)

drop_detected = False

for ddl in ddls:
    stmt = ddl["statement"]

    prompt = f"""
You are a database safety expert.

Classify the following SQL DDL as:
- reversible
- irreversible

DDL:
{stmt}

Return ONLY JSON:
{{ "classification": "reversible" }} OR {{ "classification": "irreversible" }}
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )

        result = json.loads(response.choices[0].message.content)
        classification = result["classification"].lower()

    except Exception as e:
        print("⚠ AI failed, using fallback:", e)
        classification = (
            "irreversible"
            if ddl["type"] in ("DROP", "TRUNCATE")
            else "reversible"
        )

    ddl["classification"] = classification

    if classification == "irreversible":
        drop_detected = True

    print(f"DDL [{ddl['id']}] → {classification}")

# Update global IS_DROP
data["is_drop"] = drop_detected

with open("ddl_output.json", "w") as f:
    json.dump(data, f, indent=2)

print("FINAL IS_DROP:", drop_detected)
print(f"##vso[task.setvariable variable=IS_DROP;isOutput=true]{str(drop_detected).lower()}")

print("AI Classification Complete")
