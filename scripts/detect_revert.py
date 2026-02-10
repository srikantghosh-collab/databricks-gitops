import subprocess

def git(cmd):
    return subprocess.check_output(cmd, text=True).strip()

msg = git(["git", "log", "-1", "--pretty=%B"])

is_revert = "revert" in msg.lower()

print("Commit message:", msg)
print("Is revert:", is_revert)

print(f"##vso[task.setvariable variable=IS_REVERT;isOutput=true]{str(is_revert).lower()}")
