import subprocess
import re

def git(cmd):
    return subprocess.check_output(cmd, text=True).strip()

msg = git(["git", "log", "-1", "--pretty=%B"])

# Real git revert detection
is_revert = bool(re.match(r'^Revert "', msg))

print("Commit message:", msg)
print("Is revert:", is_revert)

print(f"##vso[task.setvariable variable=IS_REVERT;isOutput=true]{str(is_revert).lower()}")

