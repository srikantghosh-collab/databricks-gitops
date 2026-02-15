import json
import os
import sys
from openai import AzureOpenAI

print("AI Classification Stage Starting...")

if not os.path.exists("ddl_output.json"):
    print("No ddl_output.json found — skipping")
    sys.exit(0)

with open("ddl_output.json", "r") as f:
    data = json.load(f)

ddls = data.get("ddls", [])

if not ddls:
    print("No DDL found — skipping")
    sys.exit(0)

client = None

# Try to initialize Azure OpenAI
try:
    client = AzureOpenAI(
        api_key=os.environ["AZURE_OPENAI_KEY"],
        azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        api_version="2024-02-15-preview"
    )
except Exception as e:
    print("AI client init failed — fallback mode:", e)


final_is_drop = False

for ddl_obj in ddls:

    ddl_stmt = ddl_obj["statement"]
    ddl_type = ddl_obj["type"]

    print("Classifying:", ddl_stmt)

    classification = None

    # Try AI if available
    if client:
        try:
            prompt = f"""
You are a SQL safety analyzer.

Classify this DDL statement:

{ddl_stmt}

Return ONLY JSON:

{{ "classification": "reversible" }}
or
{{ "classification": "irreversible" }}
"""

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0
            )

            result = json.loads(response.choices[0].message.content)
            classification = result["classification"].strip().lower()

        except Exception as e:
            print("AI failed — fallback rule used:", e)

    # Fallback rule
    if not classification:
        classification = (
            "irreversible"
            if ddl_type == "DROP"
            else "reversible"
        )

    ddl_obj["classification"] = classification

    print("→ Classified as:", classification)

    if classification == "irreversible":
        final_is_drop = True


# Update artifact with classification
with open("ddl_output.json", "w") as f:
    json.dump(data, f, indent=2)


print("FINAL IS_DROP VALUE:", final_is_drop)

print(f"##vso[task.setvariable variable=IS_DROP;isOutput=true]{str(final_is_drop).lower()}")

print("AI Classification Complete")
