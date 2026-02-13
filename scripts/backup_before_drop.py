from databricks import sql
import os
import datetime
import json

CATALOG = "hive_metastore"
SCHEMA = "default"

def backup_table(table_name):
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_table_name = f"{table_name}_backup_{timestamp}"

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
    AS SELECT * FROM {table_name}
    """

    print("Taking backup using SQL:")
    print(backup_sql)

    cursor.execute(backup_sql)

    print(f"Backup table created: {backup_table_name}")

    #  Metadata save
    metadata = {
        "catalog": CATALOG,
        "schema": SCHEMA,
        "original_table": table_name,
        "backup_table": backup_table_name,
        "timestamp": timestamp
    }

    with open("rollback_metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    print("Rollback metadata saved:")
    print(metadata)

    cursor.close()
    conn.close()

    return backup_table_name


if __name__ == "__main__":
    table_to_backup = os.environ.get("DDL_TABLE_NAME")

    if not table_to_backup:
        raise Exception("DDL_TABLE_NAME environment variable not set")

    backup_table(table_to_backup)
    