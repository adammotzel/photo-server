import psycopg
from psycopg.rows import dict_row

from src.concurrency import run_blocking
from src.config import DB_HOST, DB_NAME, DB_PORT, DB_USER, POSTGRES_APP_PW


def _connect() -> psycopg.Connection:
    """Connect to the app database."""
    return psycopg.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=POSTGRES_APP_PW,
        host=DB_HOST,
        port=DB_PORT,
        row_factory=dict_row,  # ty: ignore[invalid-argument-type]
    )


def write_photo_metadata(
    stored_filename: str,
    content_type: str | None,
    uploaded_by: str,
) -> None:
    """
    Insert new record into 'photos' table. Record 'id' is auto-incremented and
    'uploaded_at' is generated upon insert.

    Parameters
    ----------
    stored_filename : str
        Name of the file on disk.
    content_type : str | None
        File type.
    uploaded_by : str
        Username of the uploader.

    Returns
    -------
    None
    """

    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO photos (
                    stored_filename,
                    content_type,
                    uploaded_by
                )
                VALUES (
                    %s, 
                    %s,
                    %s
                )
                """,
                (stored_filename, content_type, uploaded_by),
            )

        conn.commit()


async def get_user_by_username(username: str) -> dict:
    """
    Fetch user data from database using username.

    Parameters
    ----------
    username : str
        Name of the user to lookup.

    Returns
    -------
    dict
        Dict representation of the database table record.
    """

    def _query():
        with _connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM users WHERE username = %s", (username,))
                return cur.fetchone()

    return await run_blocking(_query)


async def get_user_by_id(user_id: str) -> dict:
    """
    Fetch user data from database using user id.

    Parameters
    ----------
    user_id : str
        ID of the user to lookup.

    Returns
    -------
    dict
        Dict representation of the database table record.
    """

    def _query():
        with _connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
                return cur.fetchone()

    return await run_blocking(_query)


async def create_user(username: str, password_hash: str):
    """
    Create a new user.

    Parameters
    ----------
    username : str
        Name of the user to create.
    password_hash : str
        Hashed user password. Should be the result of auth.hash_passwrod

    Returns
    -------
    None
    """

    def _query():
        with _connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO users (username, password_hash)
                    VALUES (%s, %s)
                    RETURNING id
                    """,
                    (username, password_hash),
                )
                conn.commit()

    await run_blocking(_query)
