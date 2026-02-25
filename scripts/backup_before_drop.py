from databricks import sql
import os
import json

CATALOG = "hive_metastore"
SCHEMA = "default"


def backup_table(table_name, commit_id):
    """
    Takes a DEEP CLONE backup of a Delta table.
    Backup name is deterministic per commit.
    """

    backup_table_name = f"{table_name}__backup__{commit_id}"

    print(f"Preparing DEEP CLONE backup for table: {table_name}")
    print(f"Backup table name: {backup_table_name}")

    conn = sql.connect(
        server_hostname=os.environ["DATABRICKS_HOST"],
        http_path=os.environ["DATABRICKS_HTTP_PATH"],
        access_token=os.environ["DATABRICKS_TOKEN"]
    )

    cursor = conn.cursor()
    cursor.execute(f"USE CATALOG {CATALOG}")
    cursor.execute(f"USE SCHEMA {SCHEMA}")

    backup_sql = f"""
    CREATE TABLE {backup_table_name}
    DEEP CLONE {table_name}
    """

    print("Executing backup SQL:")
    print(backup_sql)

    cursor.execute(backup_sql)

    print(f"Backup table created successfully: {backup_table_name}")

    cursor.execute(f"""
    INSERT INTO ddl_data_backup VALUES (
       current_timestamp(),
       '{commit_id}',
       '{table_name}',
       '{backup_table_name}',
       'DATA'
    )
    """)

    # --------------------------------
    # Rollback metadata (restore-aware)
    # --------------------------------
    metadata = {
        "catalog": CATALOG,
        "schema": SCHEMA,
        "commit_id": commit_id,
        "source_table": table_name,
        "backup_table": backup_table_name,
        "backup_type": "DEEP_CLONE"
    }

    with open("rollback_metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    print("Rollback metadata saved:")
    print(json.dumps(metadata, indent=2))

    cursor.close()
    conn.close()

    return backup_table_name


# --------------------------------
# Entry point
# --------------------------------
if __name__ == "__main__":

    table_to_backup = os.environ.get("DDL_TABLE_NAME")
    commit_id = os.environ.get("COMMIT_ID")

    if not table_to_backup:
        raise Exception("DDL_TABLE_NAME environment variable not set")

    if not commit_id:
        raise Exception("COMMIT_ID environment variable not set")

    backup_table(table_to_backup, commit_id)