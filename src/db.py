from psycopg_pool import ConnectionPool

from src.config import DB_HOST, DB_NAME, DB_PORT, DB_USER, POSTGRES_APP_PW

pool = ConnectionPool(
    conninfo=(
        f"dbname={DB_NAME} "
        f"user={DB_USER} "
        f"password={POSTGRES_APP_PW} "
        f"host={DB_HOST} "
        f"port={DB_PORT}"
    ),
    min_size=2,
    max_size=10,
    timeout=30,
    open=False,
)


def write_photo_metadata(
    stored_filename: str,
    content_type: str | None,
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

    Returns
    -------
    int
        The 'id' of the new photo record.
    """

    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO photos (
                    stored_filename,
                    content_type
                )
                VALUES (
                    %s,
                    %s
                )
                RETURNING id
                """,
                (stored_filename, content_type),
            )
            row = cur.fetchone()
            if row is None:
                raise RuntimeError("Insert into 'photos' did not return an id.")
            return row[0]


def upsert_network(name: str) -> int:
    """
    Insert 'name' into the 'networks' table if it doesn't already exist, and
    return its 'id' either way.

    Parameters
    ----------
    name : str
        Name of the Wi-Fi network the app is running on.

    Returns
    -------
    int
        The 'id' of the network record (existing or newly created).
    """

    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO networks (name)
                VALUES (%s)
                ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name
                RETURNING id
                """,
                (name,),
            )
            row = cur.fetchone()
            if row is None:
                raise RuntimeError("Upsert into 'networks' did not return an id.")
            return row[0]


def write_prediction(
    photo_id: int | None,
    network_id: int | None,
    original_filename: str,
    predicted_label: str,
    confidence: float,
    uploader_ip: str,
) -> None:
    """
    Insert new record into 'predictions' table for model evaluation.

    Parameters
    ----------
    photo_id : int | None
        'id' of the related 'photos' record, or None if the upload was rejected.
    network_id : int | None
        'id' of the related 'networks' record, or None if unknown.
    original_filename : str
        Name of the file as uploaded by the user.
    predicted_label : str
        Label predicted by the classifier.
    confidence : float
        Confidence score of the predicted label.
    uploader_ip : str
        LAN IP address of the uploading device.

    Returns
    -------
    None
    """

    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO predictions (
                    photo_id,
                    network_id,
                    original_filename,
                    predicted_label,
                    confidence,
                    uploader_ip
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
                    network_id,
                    original_filename,
                    predicted_label,
                    confidence,
                    uploader_ip,
                ),
            )
