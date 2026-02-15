import re

def split_sql_statements(sql_text):
    """
    Splits SQL file into individual statements safely.
    Handles multi-line statements.
    """

    statements = []
    buffer = ""

    for line in sql_text.splitlines():
        line = line.strip()

        if not line or line.startswith("--"):
            continue

        buffer += " " + line

        if line.endswith(";"):
            statements.append(buffer.strip())
            buffer = ""

    if buffer:
        statements.append(buffer.strip())

    return statements


def extract_ddls(statements):
    ddl_list = []

    for stmt in statements:
        stmt_upper = stmt.upper()

        if stmt_upper.startswith(("CREATE", "ALTER", "DROP")):
            ddl_list.append({
                "statement": stmt,
                "type": stmt_upper.split()[0],
                "classification": None
            })

    return ddl_list


#  THIS IS WHAT execute_ddl.py EXPECTS
def parse_sql_file(file_path):
    """
    High-level parser used by pipeline execution stage
    """

    with open(file_path, "r") as f:
        sql_text = f.read()

    statements = split_sql_statements(sql_text)

    # Return only executable SQL strings
    return [s for s in statements]
