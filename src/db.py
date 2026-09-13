from psycopg_pool import ConnectionPool

from src.config import config
from src.types import GalleryPhoto

pool = ConnectionPool(
    conninfo=(
        f"dbname={config.db_name} "
        f"user={config.db_user} "
        f"password={config.db_password.get_secret_value()} "
        f"host={config.db_host} "
        f"port={config.db_port}"
    ),
    min_size=2,
    max_size=10,
    timeout=30,
    open=False,
)


def write_description(
    photo_id: int,
    description: str,
    input_tokens: int,
    output_tokens: int,
    model: str,
) -> None:
    """
    Insert new record into 'descriptions' table and link it from its 'photos'
    record, in one transaction. Record 'id' is auto-incremented and
    'generated_at' is generated upon insert.

    Descriptions are written in the background after the photo is saved, so
    the insert and the link must commit together: otherwise a failure between
    them would leave a 'descriptions' row no photo points to.

    Parameters
    ----------
    photo_id : int
        'id' of the 'photos' record the description belongs to.
    description : str
        LLM-written description of the photo.
    input_tokens : int
        Tokens billed for the prompt, including the image.
    output_tokens : int
        Tokens billed for the description.
    model : str
        Model that wrote the description.

    Returns
    -------
    None

    Raises
    ------
    RuntimeError
        If no 'photos' record has id `photo_id`. Nothing is written.
    """

    # the connection block commits on a clean exit and rolls back if anything
    # raises, so both statements land or neither does
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO descriptions (
                    description,
                    input_tokens,
                    output_tokens,
                    model
                )
                VALUES (
                    %s,
                    %s,
                    %s,
                    %s
                )
                RETURNING id
                """,
                (description, input_tokens, output_tokens, model),
            )
            row = cur.fetchone()
            if row is None:
                raise RuntimeError("Insert into 'descriptions' did not return an id.")

            cur.execute(
                "UPDATE photos SET description_id = %s WHERE id = %s",
                (row[0], photo_id),
            )
            if cur.rowcount != 1:
                raise RuntimeError(f"No 'photos' record with id {photo_id}.")


def write_photo_metadata(stored_filename: str, content_type: str | None) -> int:
    """
    Insert new record into 'photos' table. Record 'id' is auto-incremented and
    'uploaded_at' is generated upon insert. 'description_id' starts null; see
    `write_description`.

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


def get_photo_count() -> int:
    """
    Count the total number of records in the 'photos' table.

    Returns
    -------
    int
        Total number of saved photos.
    """

    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM photos")
            row = cur.fetchone()
            return row[0] if row else 0


def get_photos(limit: int, offset: int) -> list[GalleryPhoto]:
    """
    Fetch a page of photos from the 'photos' table, joined to their
    descriptions, newest upload first.

    Parameters
    ----------
    limit : int
        Maximum number of photos to return.
    offset : int
        Number of newest-first rows to skip before collecting results.

    Returns
    -------
    list[GalleryPhoto]
        Stored filename and description for the requested page, ordered by
        'uploaded_at' descending ('id' descending breaks ties from
        same-timestamp uploads).
    """

    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT p.stored_filename, d.description
                FROM photos p
                LEFT JOIN descriptions d ON d.id = p.description_id
                ORDER BY p.uploaded_at DESC, p.id DESC
                LIMIT %s OFFSET %s
                """,
                (limit, offset),
            )
            return [GalleryPhoto(*row) for row in cur.fetchall()]


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
