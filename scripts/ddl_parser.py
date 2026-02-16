import re

def split_sql_statements(sql_text):
    """
    Split SQL file into individual statements using semicolon.
    Handles multi-line DDLs safely.
    """

    statements = []
    buffer = ""

    for line in sql_text.splitlines():
        line = line.strip()

        # Skip comments & empty lines
        if not line or line.startswith("--"):
            continue

        buffer += " " + line

        if line.endswith(";"):
            statements.append(buffer.strip().rstrip(";"))
            buffer = ""

    if buffer.strip():
        statements.append(buffer.strip())

    return statements


def extract_ddls(statements):
    """
    Extract DDL statements with metadata
    """

    ddls = []
    counter = 1

    for stmt in statements:
        stmt_upper = stmt.upper()

        if stmt_upper.startswith(("CREATE", "ALTER", "DROP", "TRUNCATE")):

            table = extract_table_name(stmt_upper)

            ddls.append({
                "id": f"ddl_{counter}",
                "statement": stmt,
                "type": stmt_upper.split()[0],
                "table": table
            })

            counter += 1

    return ddls


def extract_table_name(stmt_upper):
    """
    Extract table name from DDL
    """

    patterns = [
        r"CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+([^\s(]+)",
        r"CREATE\s+TABLE\s+([^\s(]+)",
        r"ALTER\s+TABLE\s+([^\s]+)",
        r"DROP\s+TABLE\s+IF\s+EXISTS\s+([^\s]+)",
        r"DROP\s+TABLE\s+([^\s]+)",
        r"TRUNCATE\s+TABLE\s+([^\s]+)"
    ]

    for pattern in patterns:
        match = re.search(pattern, stmt_upper)
        if match:
            return match.group(1)

    return None
