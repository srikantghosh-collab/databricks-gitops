import subprocess
import sys

try:
    msg = subprocess.check_output(
        ["git", "log", "-1", "--pretty=%B"],
        text=True
    )
except:
    print("##vso[task.setvariable variable=IS_REVERT;isOutput=true]false")
    sys.exit(0)

if msg.startswith("Revert"):
    commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD~1"],
        text=True
    ).strip()

    print("Git revert detected")
    print(f"##vso[task.setvariable variable=IS_REVERT;isOutput=true]true")
    print(f"##vso[task.setvariable variable=REVERT_COMMIT;isOutput=true]{commit}")
else:
    print("##vso[task.setvariable variable=IS_REVERT;isOutput=true]false")
