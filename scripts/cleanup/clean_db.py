"""
Remove records from 'photos' table if the associated photo does not actually 
exist.

You'll need a .env file in this directory with one secret, POSTGRES_PW.
"""
import os
import psycopg

from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "photoapp",
    "user": "photoapp_user",
    "password": os.getenv("POSTGRES_PW")
}

TABLE_NAME = "photos"
FILENAME_COLUMN = "stored_filename"

SEARCH_DIRS = [
    "src/photos",
]


def file_exists(filename):
    for directory in SEARCH_DIRS:
        full_path = os.path.join(directory, filename)
        if os.path.isfile(full_path):
            return True
    return False


def main():
    conn = psycopg.connect(**DB_CONFIG)
    cur = conn.cursor()

    cur.execute(f"""
        SELECT {FILENAME_COLUMN}
        FROM {TABLE_NAME}
    """)

    rows = cur.fetchall()

    deleted_count = 0

    for info in rows:

        filename = info[0]

        if not filename:
            continue

        if not file_exists(filename):
            print(f"Missing file: {filename} -> deleting row")

            cur.execute(
                f"DELETE FROM {TABLE_NAME} WHERE {FILENAME_COLUMN} = %s",
                (filename,)
            )

            deleted_count += 1

    conn.commit()

    print(f"Deleted {deleted_count} rows")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
    