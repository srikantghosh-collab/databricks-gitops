import subprocess
import sys
import re

try:
    msg = subprocess.check_output(
        ["git", "log", "-1", "--pretty=%B"],
        text=True
    )
except Exception:
    print("##vso[task.setvariable variable=IS_REVERT;isOutput=true]false")
    sys.exit(0)

# Check if this is a revert commit
if msg.startswith("Revert"):
    print("Git revert detected")

    # Extract original commit id from revert message
    match = re.search(r"This reverts commit ([a-f0-9]+)", msg)

    if not match:
        print("ERROR: Could not extract reverted commit id")
        print("##vso[task.setvariable variable=IS_REVERT;isOutput=true]false")
        sys.exit(1)

    reverted_commit = match.group(1)

    print(f"Reverted commit detected: {reverted_commit}")

    print("##vso[task.setvariable variable=IS_REVERT;isOutput=true]true")
    print(f"##vso[task.setvariable variable=REVERT_COMMIT;isOutput=true]{reverted_commit}")

else:
    print("##vso[task.setvariable variable=IS_REVERT;isOutput=true]false")
