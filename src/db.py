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
    max_size=10,  # can be changed
    timeout=30,
    open=False,
)


def write_photo_metadata(
    stored_filename: str,
    content_type: str | None,
    uploader_ip: str,
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
    uploader_ip : str
        LAN IP address of the uploading device.

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
                    content_type,
                    uploader_ip
                )
                VALUES (
                    %s,
                    %s,
                    %s
                )
                RETURNING id
                """,
                (stored_filename, content_type, uploader_ip),
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
    uploader_ip: str,
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
                    original_filename,
                    predicted_label,
                    confidence,
                    accepted,
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
                    original_filename,
                    predicted_label,
                    confidence,
                    accepted,
                    uploader_ip,
                ),
            )
