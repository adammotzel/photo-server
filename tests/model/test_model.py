import base64
import io
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from PIL import Image

from src.config import DESCRIPTION_MAX_PX, OPENAI_MODEL
from src.model import _encode_for_description, describe_image, inference, load_model
from src.types import Description

MODEL_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "models" / "efficientnet-b0-dog-classifier"
)


def test_inference_returns_known_label_and_probability(sample_image_bytes):
    """
    Verify the real classifier returns one of its known labels with a
    confidence in `[0, 1]`.
    """
    processor, model = load_model(str(MODEL_PATH))

    label, confidence = inference(processor, model, sample_image_bytes)

    assert label in model.config.id2label.values()
    assert isinstance(confidence, float)
    assert 0.0 <= confidence <= 1.0


def test_encode_for_description_downscales(sample_image_bytes):
    """
    Verify the image sent to the vision model is a JPEG bounded to
    `DESCRIPTION_MAX_PX`, not the full-size original.
    """
    with Image.open(io.BytesIO(sample_image_bytes)) as original:
        assert max(original.size) > DESCRIPTION_MAX_PX  # guard against a vacuous pass

    decoded = base64.b64decode(_encode_for_description(sample_image_bytes))

    with Image.open(io.BytesIO(decoded)) as image:
        assert image.format == "JPEG"
        assert max(image.size) == DESCRIPTION_MAX_PX


def test_describe_image_returns_model_text(monkeypatch, sample_image_bytes):
    """
    Verify `describe_image` sends the encoded image to the configured model and
    returns its stripped text, token usage, and model name.
    """
    mock_client = MagicMock()
    response = mock_client.responses.create.return_value
    response.output_text = "  Such dog.  "
    response.usage.input_tokens = 123
    response.usage.output_tokens = 45
    response.model = "gpt-4o-mini-2024-07-18"
    monkeypatch.setattr("src.model.get_openai_client", lambda: mock_client)

    description = describe_image(sample_image_bytes)

    assert description == Description(
        description="Such dog.",
        input_tokens=123,
        output_tokens=45,
        model="gpt-4o-mini-2024-07-18",
    )

    kwargs = mock_client.responses.create.call_args.kwargs
    assert kwargs["model"] == OPENAI_MODEL
    image_url = kwargs["input"][0]["content"][1]["image_url"]
    assert image_url.startswith("data:image/jpeg;base64,")


def test_describe_image_raises_without_usage(monkeypatch, sample_image_bytes):
    """
    Verify a response missing token usage raises instead of recording a
    description with unknown cost.
    """
    mock_client = MagicMock()
    mock_client.responses.create.return_value.usage = None
    monkeypatch.setattr("src.model.get_openai_client", lambda: mock_client)

    with pytest.raises(RuntimeError, match="token usage"):
        describe_image(sample_image_bytes)
