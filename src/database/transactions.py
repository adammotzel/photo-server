from sqlalchemy import create_engine, func, select, update
from sqlalchemy.engine import URL
from sqlalchemy.orm import Session

from src.config import config
from src.database.tables import Descriptions, Networks, Photos, Predictions
from src.types import GalleryPhoto

engine = create_engine(
    URL.create(
        drivername="postgresql+psycopg",
        username=config.db_user,
        password=config.db_password.get_secret_value(),
        host=config.db_host,
        port=config.db_port,
        database=config.db_name,
    ),
    pool_size=2,
    max_overflow=8,
    pool_timeout=30,
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
    them would leave a 'descriptions' row that no photo points to.

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
    with Session(engine) as session:
        with session.begin():
            record = Descriptions(
                description=description,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                model=model,
            )
            session.add(record)
            session.flush()

            result = session.execute(
                update(Photos)
                .where(Photos.id == photo_id)
                .values(description_id=record.id)
            )

            if result.rowcount != 1:
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
    with Session(engine) as session:
        with session.begin():
            record = Photos(
                stored_filename=stored_filename,
                content_type=content_type,
            )
            session.add(record)
            session.flush()

            return record.id


def get_photo_count() -> int:
    """
    Count the total number of records in the 'photos' table.

    Returns
    -------
    int
        Total number of saved photos.
    """
    with Session(engine) as session:
        result = session.scalar(select(func.count()).select_from(Photos))

        return result or 0


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

    stmt = (
        select(Photos.stored_filename, Descriptions.description)
        .outerjoin(
            Descriptions,
            Descriptions.id == Photos.description_id,
        )
        .order_by(Photos.uploaded_at.desc(), Photos.id.desc())
        .limit(limit)
        .offset(offset)
    )

    with Session(engine) as session:
        rows = session.execute(stmt).all()

        return [GalleryPhoto(*row) for row in rows]


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

    with Session(engine) as session:
        with session.begin():
            network = session.scalar(select(Networks).where(Networks.name == name))

            if network is not None:
                return network.id

            record = Networks(name=name)
            session.add(record)
            session.flush()

            return record.id


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

    with Session(engine) as session:
        with session.begin():
            record = Predictions(
                photo_id=photo_id,
                network_id=network_id,
                original_filename=original_filename,
                predicted_label=predicted_label,
                confidence=confidence,
                uploader_ip=uploader_ip,
            )
            session.add(record)
            session.flush()
