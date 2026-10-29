import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Networks(Base):
    """
    A dynamically updated table of Wi-Fi networks.

    New entries are inserted into the table during app startup,
    based on the `NETWORK_NAME` environment variable.
    """

    __tablename__ = "networks"

    id: Mapped[int] = mapped_column(primary_key=True)

    name: Mapped[str] = mapped_column(String(255), unique=True)


class Descriptions(Base):
    """LLM-generated image descriptions."""

    __tablename__ = "descriptions"

    id: Mapped[int] = mapped_column(primary_key=True)

    description: Mapped[str] = mapped_column(Text)
    input_tokens: Mapped[int] = mapped_column(Integer)
    output_tokens: Mapped[int] = mapped_column(Integer)
    generated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    model: Mapped[str] = mapped_column(String(30))


class Photos(Base):
    """Uploaded photos."""

    __tablename__ = "photos"

    id: Mapped[int] = mapped_column(primary_key=True)
    description_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("descriptions.id"),
        nullable=True,
    )

    stored_filename: Mapped[str] = mapped_column(String(255), unique=True)
    content_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    uploaded_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


class Predictions(Base):
    """Dog classifier predictions."""

    __tablename__ = "predictions"

    id: Mapped[int] = mapped_column(primary_key=True)
    photo_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("photos.id"),
        nullable=True,
    )
    network_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("networks.id"),
        nullable=True,
    )

    original_filename: Mapped[str] = mapped_column(String(255))
    predicted_label: Mapped[str] = mapped_column(String(255))
    confidence: Mapped[float] = mapped_column(Float)
    uploader_ip: Mapped[str] = mapped_column(String(30))
    predicted_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
