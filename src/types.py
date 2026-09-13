from typing import NamedTuple


class Description(NamedTuple):
    """
    An LLM-written photo description, plus the metadata stored alongside it.

    Attributes
    ----------
    description : str
        The model's description of the image.
    input_tokens : int
        Tokens billed for the prompt, including the image.
    output_tokens : int
        Tokens billed for the description.
    model : str
        Model that wrote the description, as reported by the API.
    """

    description: str
    input_tokens: int
    output_tokens: int
    model: str


class GalleryPhoto(NamedTuple):
    """
    A photo as the gallery needs it.

    Attributes
    ----------
    stored_filename : str
        Name of the file on disk, used to build its '/thumbnails/...' and
        '/photos/...' URLs.
    description : str | None
        LLM-written description of the photo, revealed when the viewer opens
        the tile. None for photos uploaded before descriptions existed, whose
        description failed to generate, or whose description is still being
        written in the background.
    """

    stored_filename: str
    description: str | None


class PendingDescription(NamedTuple):
    """
    A saved photo waiting on its background description.

    Attributes
    ----------
    photo_id : int
        'id' of the photo's 'photos' record.
    original_filename : str
        Filename as submitted by the uploading client, for logging.
    contents : bytes
        Contents of the photo, sent to the LLM.
    """

    photo_id: int
    original_filename: str
    contents: bytes


class UploadResult(NamedTuple):
    """
    Outcome of a single file's trip through the upload pipeline.

    Attributes
    ----------
    accepted : bool
        Whether the file passed validation and classification and was saved.
    original_filename : str
        Filename as submitted by the uploading client. Empty if none was sent.
    stored_filename : str | None
        Name the photo was saved under on disk (uuid + original extension),
        used to build its '/thumbnails/...' URL. None for a rejected upload,
        whose bytes never reach disk.
    reason : str | None
        Why the upload was rejected, for display. None when accepted.
    """

    accepted: bool
    original_filename: str
    stored_filename: str | None = None
    reason: str | None = None
