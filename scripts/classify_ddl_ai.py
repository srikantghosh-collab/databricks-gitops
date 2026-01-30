import os, json
from openai import AzureOpenAI

with open("ddl_output.json") as f:
    ddl = json.load(f)["ddl"]

ddl_upper = ddl.upper()

# HARD RULES
if "DROP TABLE" in ddl_upper:
    result = {"type": "irreversible", "risk": "Data loss", "source": "rule"}
else:
    client = AzureOpenAI(
        api_key=os.getenv("AZURE_OPENAI_KEY"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_version="2024-02-15-preview"
    )

    prompt = f"""
Classify this DDL as reversible or irreversible and explain risk.
Respond only in JSON.

DDL:
{ddl}
"""

    res = client.chat.completions.create(
        model=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )

    result = json.loads(res.choices[0].message.content)
    result["source"] = "ai"

with open("classification.json", "w") as f:
    json.dump(result, f, indent=2)

print(result)
