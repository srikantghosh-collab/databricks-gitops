import subprocess, json, sys

diff = subprocess.check_output(["git", "diff", "HEAD~1", "HEAD"], text=True)

keywords = ["CREATE TABLE", "ALTER TABLE", "DROP TABLE"]
ddl = None

for line in diff.splitlines():
    if any(k in line.upper() for k in keywords):
        ddl = line.replace("+", "").strip()
        break

if not ddl:
    print("NO DDL FOUND")
    sys.exit(0)

with open("ddl_output.json", "w") as f:
    json.dump({"ddl": ddl}, f)

print("Detected DDL:", ddl)
