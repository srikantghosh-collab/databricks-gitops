# import subprocess
# import sys
# import re

# print("Checking if this is a Git revert commit...")

# # -----------------------------------------
# # Read latest commit message
# # -----------------------------------------
# try:
#     msg = subprocess.check_output(
#         ["git", "log", "-1", "--pretty=%B"],
#         text=True
#     ).strip()
# except Exception as e:
#     print("Failed to read git commit message:", str(e))
#     print("##vso[task.setvariable variable=IS_REVERT;isOutput=true]false")
#     sys.exit(0)

# print("Latest commit message:")
# print(msg)

# # -----------------------------------------
# # Detect revert commit (case-insensitive)
# # -----------------------------------------
# if re.search(r"\brevert\b", msg, re.IGNORECASE):

#     print("Revert keyword detected in commit message")

#     # -------------------------------------
#     # Extract original commit id
#     # -------------------------------------
#     match = re.search(
#         r"reverts commit\s+([a-f0-9]{7,40})",
#         msg,
#         re.IGNORECASE
#     )

#     if not match:
#         print("ERROR: Revert commit detected but original commit id not found")
#         print("##vso[task.setvariable variable=IS_REVERT;isOutput=true]false")
#         sys.exit(1)

#     reverted_commit = match.group(1).lower()

#     print(f"Reverted commit detected: {reverted_commit}")

#     # -------------------------------------
#     # Azure DevOps output variables
#     # -------------------------------------
#     print("##vso[task.setvariable variable=IS_REVERT;isOutput=true]true")
#     print(f"##vso[task.setvariable variable=REVERT_COMMIT;isOutput=true]{reverted_commit}")

# else:
#     print("No revert detected in commit message")
#     print("##vso[task.setvariable variable=IS_REVERT;isOutput=true]false")import subprocess
# import sys
# import re

# print("Checking if this is a Git revert commit...")

# # -----------------------------------------
# # Read latest commit message
# # -----------------------------------------
# try:
#     msg = subprocess.check_output(
#         ["git", "log", "-1", "--pretty=%B"],
#         text=True
#     ).strip()
# except Exception as e:
#     print("Failed to read git commit message:", str(e))
#     print("##vso[task.setvariable variable=IS_REVERT;isOutput=true]false")
#     sys.exit(0)

# print("Latest commit message:")
# print(msg)

# # -----------------------------------------
# # Detect revert commit (case-insensitive)
# # -----------------------------------------
# if re.search(r"\brevert\b", msg, re.IGNORECASE):

#     print("Revert keyword detected in commit message")

#     # -------------------------------------
#     # Extract original commit id
#     # -------------------------------------
#     match = re.search(
#         r"reverts commit\s+([a-f0-9]{7,40})",
#         msg,
#         re.IGNORECASE
#     )

#     if not match:
#         print("ERROR: Revert commit detected but original commit id not found")
#         print("##vso[task.setvariable variable=IS_REVERT;isOutput=true]false")
#         sys.exit(1)

#     reverted_commit = match.group(1).lower()

#     print(f"Reverted commit detected: {reverted_commit}")

#     # -------------------------------------
#     # Azure DevOps output variables
#     # -------------------------------------
#     print("##vso[task.setvariable variable=IS_REVERT;isOutput=true]true")
#     print(f"##vso[task.setvariable variable=REVERT_COMMIT;isOutput=true]{reverted_commit}")

# else:
#     print("No revert detected in commit message")
#     print("##vso[task.setvariable variable=IS_REVERT;isOutput=true]false")



import subprocess
import sys
import re

print("Checking if this is a Git revert commit...")

# -----------------------------------------
# Read latest commit message
# -----------------------------------------
try:
    msg = subprocess.check_output(
        ["git", "log", "-1", "--pretty=%B"],
        text=True
    ).strip()
except Exception as e:
    print("Failed to read git commit message:", str(e))
    print("##vso[task.setvariable variable=IS_REVERT;isOutput=true]false")
    sys.exit(0)

print("Latest commit message:")
print("-----")
print(msg)
print("-----")

# -----------------------------------------
# Detect revert commit
# -----------------------------------------
# Git standard revert formats:
# 1) Revert "commit message"
#    This reverts commit <hash>
#
# 2) revert: <something>
#
is_revert = False
original_commit = None

if re.search(r"\brevert\b", msg, re.IGNORECASE):
    is_revert = True

    # Try to extract ORIGINAL commit id
    match = re.search(
        r"(?:this\s+reverts\s+commit|reverts\s+commit)\s+([a-f0-9]{7,40})",
        msg,
        re.IGNORECASE
    )

    if match:
        original_commit = match.group(1).lower()
    else:
        print("ERROR: Revert detected but original commit id not found")
        print("Commit message format not supported")
        print("##vso[task.setvariable variable=IS_REVERT;isOutput=true]false")
        sys.exit(1)

# -----------------------------------------
# Azure DevOps output variables
# -----------------------------------------
if is_revert:
    print(f"Git revert detected. Original commit: {original_commit}")

    print("##vso[task.setvariable variable=IS_REVERT;isOutput=true]true")
    print(f"##vso[task.setvariable variable=REVERT_COMMIT;isOutput=true]{original_commit}")
else:
    print("No git revert detected")
    print("##vso[task.setvariable variable=IS_REVERT;isOutput=true]false")