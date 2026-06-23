def fetch_all_parser(cursor):
    col = [col[0] for col in cursor.description]

    return [
        dict(zip(col, row)) for row in cursor.fetchall()
    ]