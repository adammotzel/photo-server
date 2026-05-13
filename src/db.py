import psycopg

from src.config import POSTGRES_APP_PW


def _connect() -> psycopg.Connection:
    """Connect to the pricing service database."""
    return psycopg.connect(
        dbname="photoapp",
        user="photoapp_user",
        password=POSTGRES_APP_PW,
        host="localhost",
        port="5432",
    )


def write_photo_metadata(
    stored_filename: str,
    content_type: str | None,
    uploaded_by: str,
) -> None:
    """
    Insert new record into 'photos' table. Record 'id' is auto-incremented and
    'uploaded_at' is generated upon insert.
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
