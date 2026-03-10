from databricks import sql
import os
import sys

print("Starting rollback restore process")

PIPELINE_IS_REVERT = os.environ.get("PIPELINE_IS_REVERT", "no").lower()
if PIPELINE_IS_REVERT != "yes":
    print("Not a revert → exiting")
    sys.exit(0)

REVERT_COMMIT = os.environ.get("REVERT_COMMIT")

if not REVERT_COMMIT:
    print("REVERT_COMMIT missing")
    sys.exit(1)

conn = sql.connect(
    server_hostname=os.environ["DATABRICKS_HOST"],
    http_path=os.environ["DATABRICKS_HTTP_PATH"],
    access_token=os.environ["DATABRICKS_TOKEN"],
)

cursor = conn.cursor()

cursor.execute("USE CATALOG hive_metastore")
cursor.execute("USE SCHEMA ddl_backup_table")

print("Searching backup tables...")

cursor.execute("SHOW TABLES")

tables = cursor.fetchall()

restored = False

for row in tables:

    table_name = row[1]

    if REVERT_COMMIT in table_name:

        backup_table = f"hive_metastore.ddl_backup_table.{table_name}"

        source_table = table_name.replace(f"_backup_{REVERT_COMMIT}", "")

        source_table = f"hive_metastore.default.{source_table}"

        print(f"Restoring {source_table} from {backup_table}")

        cursor.execute(f"DROP TABLE IF EXISTS {source_table}")

        cursor.execute(f"""
        CREATE TABLE {source_table}
        DEEP CLONE {backup_table}
        """)

        restored = True

if not restored:
    print("No matching backup table found")

cursor.close()
conn.close()

print("Rollback finished")