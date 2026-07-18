from typing import Any

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from src.config import DB_HOST, DB_NAME, DB_PORT, DB_USER, POSTGRES_APP_PW
from src.logger import logger

pool = ConnectionPool(
    conninfo=(
        f"dbname={DB_NAME} "
        f"user={DB_USER} "
        f"password={POSTGRES_APP_PW} "
        f"host={DB_HOST} "
        f"port={DB_PORT}"
    ),
    min_size=2,
    max_size=10,  # can be changed
    timeout=30,
    open=False,
)


def write_photo_metadata(
    stored_filename: str,
    content_type: str | None,
    uploaded_by: str,
) -> int:
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
    int
        The 'id' of the new photo record.
    """

    logger.info(f"Writing metadata for {stored_filename}...")

    with pool.connection() as conn:
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
                RETURNING id
                """,
                (stored_filename, content_type, uploaded_by),
            )
            row = cur.fetchone()
            if row is None:
                raise RuntimeError("Insert into 'photos' did not return an id.")
            return row[0]


def write_prediction(
    photo_id: int | None,
    original_filename: str,
    predicted_label: str,
    confidence: float,
    accepted: bool,
    uploaded_by: str,
) -> None:
    """
    Insert new record into 'predictions' table for model evaluation.

    Parameters
    ----------
    photo_id : int | None
        'id' of the related 'photos' record, or None if the upload was rejected.
    original_filename : str
        Name of the file as uploaded by the user.
    predicted_label : str
        Label predicted by the classifier.
    confidence : float
        Confidence score of the predicted label.
    accepted : bool
        Whether the photo passed classification and was saved.
    uploaded_by : str
        Username of the uploader.

    Returns
    -------
    None
    """

    logger.info(f"Writing prediction for {original_filename}...")

    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO predictions (
                    photo_id,
                    original_filename,
                    predicted_label,
                    confidence,
                    accepted,
                    uploaded_by
                )
                VALUES (
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s
                )
                """,
                (
                    photo_id,
                    original_filename,
                    predicted_label,
                    confidence,
                    accepted,
                    uploaded_by,
                ),
            )


def get_user_by_username(username: str) -> dict[str, Any] | None:
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

    with pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("SELECT * FROM users WHERE username = %s", (username,))
            return cur.fetchone()


def get_user_by_id(user_id: str) -> dict[str, Any] | None:
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

    with pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
            return cur.fetchone()


def create_user(username: str, password_hash: str):
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

    logger.info("Creating new user...")

    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO users (username, password_hash)
                VALUES (%s, %s)
                """,
                (username, password_hash),
            )
