import json
import os
import re

print("Generating rollback script...")

rollback_sql = "-- No rollback required"

if os.path.exists("ddl_output.json"):

    with open("ddl_output.json") as f:
        data = json.load(f)

    ddl = data.get("ddl")

    if ddl:

        ddl_upper = ddl.upper()

        # =========================
        # CREATE → DROP
        # =========================
        if ddl_upper.startswith("CREATE TABLE"):

            match = re.search(
                r"CREATE TABLE\s+([^\s(]+)",
                ddl,
                re.IGNORECASE
            )

            if match:
                table = match.group(1)
                rollback_sql = f"DROP TABLE IF EXISTS {table};"

        # =========================
        # ALTER TABLE handler
        # =========================
        elif ddl_upper.startswith("ALTER TABLE"):

            table_match = re.search(
                r"ALTER TABLE\s+([^\s]+)",
                ddl,
                re.IGNORECASE
            )

            if not table_match:
                rollback_sql = "-- Could not detect table name"

            else:
                table = table_match.group(1)

                # ADD COLUMN
                add_match = re.search(
                    r"ADD COLUMN\s+([^\s]+)",
                    ddl,
                    re.IGNORECASE
                )

                # RENAME COLUMN
                rename_match = re.search(
                    r"RENAME COLUMN\s+([^\s]+)\s+TO\s+([^\s]+)",
                    ddl,
                    re.IGNORECASE
                )

                # DROP COLUMN
                drop_match = re.search(
                    r"DROP COLUMN\s+([^\s]+)",
                    ddl,
                    re.IGNORECASE
                )

                if add_match:
                    column = add_match.group(1)

                    rollback_sql = f"""
ALTER TABLE {table}
DROP COLUMN {column};
"""

                elif rename_match:
                    old_col = rename_match.group(1)
                    new_col = rename_match.group(2)

                    rollback_sql = f"""
ALTER TABLE {table}
RENAME COLUMN {new_col} TO {old_col};
"""

                elif drop_match:
                    rollback_sql = (
                        "-- DROP COLUMN detected: restore from backup required"
                    )

                else:
                    rollback_sql = "-- Unsupported ALTER operation"

        # =========================
        # DROP → restore
        # =========================
        elif ddl_upper.startswith("DROP TABLE"):

            if os.path.exists("rollback_metadata.json"):

                with open("rollback_metadata.json") as mf:
                    meta = json.load(mf)

                original = meta["original_table"]
                backup = meta["backup_table"]

                rollback_sql = f"""
DROP TABLE IF EXISTS {original};
CREATE TABLE {original}
AS SELECT * FROM {backup};
"""

            else:
                rollback_sql = "-- Metadata not found: manual restore required"

# Always create file
with open("rollback.sql", "w") as f:
    f.write(rollback_sql)

print("Rollback script generated:")
print(rollback_sql)
