import json
import os
import re

print("Generating rollback script...")

rollback_statements = []

if not os.path.exists("ddl_output.json"):
    print("No ddl_output.json found")
else:

    with open("ddl_output.json") as f:
        data = json.load(f)

    ddls = data.get("ddls", [])

    # Reverse execution order
    for ddl_obj in reversed(ddls):

        ddl = ddl_obj["statement"]
        ddl_type = ddl_obj.get("type", "").upper()
        classification = ddl_obj.get("classification", "").lower()

        ddl_upper = ddl.upper()

        print("Processing for rollback:", ddl)

        # ====================================
        # CREATE TABLE → DROP TABLE
        # ====================================
        if ddl_type == "CREATE":

            match = re.search(
                r"CREATE TABLE\s+(IF NOT EXISTS\s+)?([^\s(]+)",
                ddl,
                re.IGNORECASE
            )

            if match:
                table = match.group(2)
                rollback_statements.append(
                    f"DROP TABLE IF EXISTS {table};"
                )

        # ====================================
        # ALTER TABLE
        # ====================================
        elif ddl_type == "ALTER":

            table_match = re.search(
                r"ALTER TABLE\s+([^\s]+)",
                ddl,
                re.IGNORECASE
            )

            if not table_match:
                rollback_statements.append(
                    "-- Could not detect table name for ALTER"
                )
                continue

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

                rollback_statements.append(
                    f"ALTER TABLE {table} DROP COLUMN {column};"
                )

            elif rename_match:
                old_col = rename_match.group(1)
                new_col = rename_match.group(2)

                rollback_statements.append(
                    f"ALTER TABLE {table} RENAME COLUMN {new_col} TO {old_col};"
                )

            elif drop_match:
                rollback_statements.append(
                    f"-- DROP COLUMN detected on {table}: manual restore required"
                )

            else:
                rollback_statements.append(
                    f"-- Unsupported ALTER operation on {table}"
                )

        # ====================================
        # DROP TABLE → Restore from backup
        # ====================================
        elif ddl_type == "DROP":

            if os.path.exists("rollback_metadata.json"):

                with open("rollback_metadata.json") as mf:
                    meta = json.load(mf)

                original = meta["original_table"]
                backup = meta["backup_table"]

                rollback_statements.append(
                    f"DROP TABLE IF EXISTS {original};"
                )

                rollback_statements.append(
                    f"CREATE TABLE {original} AS SELECT * FROM {backup};"
                )

            else:
                rollback_statements.append(
                    "-- Metadata not found for DROP: manual restore required"
                )

        # ====================================
        # Unsupported DDL
        # ====================================
        else:
            rollback_statements.append(
                f"-- Unsupported DDL type: {ddl_type}"
            )


# If nothing generated
if not rollback_statements:
    rollback_sql = "-- No rollback required"
else:
    rollback_sql = "\n".join(rollback_statements)


with open("rollback.sql", "w") as f:
    f.write(rollback_sql)

print("Rollback script generated:")
print(rollback_sql)
