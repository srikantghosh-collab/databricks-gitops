import json
from datetime import datetime

entry = {
    "time": datetime.utcnow().isoformat(),
}

for file in ["ddl_output.json", "classification.json"]:
    try:
        with open(file) as f:
            entry.update(json.load(f))
    except:
        pass

ledger = "ledger/ddl_audit.json"

data = []
try:
    with open(ledger) as f:
        data = json.load(f)
except:
    pass

data.append(entry)

with open(ledger, "w") as f:
    json.dump(data, f, indent=2)

print("Ledger updated")
