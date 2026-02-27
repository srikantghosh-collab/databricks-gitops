import subprocess
import re
import sys

def git_commit_message(ref="HEAD"):
    try:
        return subprocess.check_output(["git", "log", "-1", "--pretty=%B", ref], text=True).strip()
    except subprocess.CalledProcessError:
        return ""

def find_reverted_commit(msg):
    # Matches "This reverts commit <sha>." or variations
    m = re.search(r"This reverts commit\s+([0-9a-fA-F]{7,40})", msg)
    if m:
        return m.group(1)
    # Some revert messages include "revert '<msg>'" without SHA — try to find SHA in body
    m2 = re.search(r"revert[^0-9a-fA-F]*([0-9a-fA-F]{7,40})", msg, re.IGNORECASE)
    if m2:
        return m2.group(1)
    return None

msg = git_commit_message("HEAD")
reverted = find_reverted_commit(msg)

# is_revert = bool(reverted)
is_revert = bool(reverted)
is_revert_str = "yes" if is_revert else "no"
revert_commit = reverted or ""

# Emit pipeline output variables (isOutput=true so they are available via dependencies / stageDependencies)
# Use lowercase 'true'/'false' for consistency with YAML checks
print("execution started")
print(f"Detected git commit message: {msg}")
#print(f"##vso[task.setvariable variable=IS_REVERT;isOutput=true]{str(is_revert).lower()}")
print(f"##vso[task.setvariable variable=is_revert_str;isOutput=true]{is_revert_str}")
print(f"is_revert: {is_revert}")
print(f"##vso[task.setvariable variable=REVERT_COMMIT;isOutput=true]{revert_commit}")
print(f"revert_commit: {revert_commit}")
print(f"##vso[task.setvariable variable=PIPELINE_IS_REVERT]{is_revert_str}")
# exit 0 so pipeline continues