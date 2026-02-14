

def parse_sql_file(file_path):
    """
    Reads a SQL file and splits it into executable DDL statements.
    Handles multi-line DDL properly.
    """

    with open(file_path, "r") as f:
        full_sql = f.read()

    statements = []
    current_stmt = ""

    for line in full_sql.splitlines():

        stripped = line.strip()

        # Skip empty lines & comments
        if not stripped or stripped.startswith("--"):
            continue

        current_stmt += stripped + " "

        # End of statement
        if stripped.endswith(";"):
            statements.append(current_stmt.strip().rstrip(";"))
            current_stmt = ""

    return statements
