import base64
import io
from functools import cache

import torch
from openai import OpenAI
from openai.types.responses import ResponseInputParam
from PIL import Image, ImageOps
from transformers import AutoImageProcessor, AutoModelForImageClassification
from transformers.image_processing_utils import BaseImageProcessor
from transformers.modeling_utils import PreTrainedModel

from src.config import (
    DESCRIPTION_MAX_PX,
    DESCRIPTION_QUALITY,
    OPENAI_MAX_RETRIES,
    OPENAI_MODEL,
    OPENAI_TIMEOUT_S,
)
from src.types import Description


def inference(
    processor: BaseImageProcessor,
    model: PreTrainedModel,
    contents: bytes,
) -> tuple[str, float]:
    """
    Check if an image contains a dog.

    Parameters
    ----------
    processor : BaseImageProcessor
        The image processor.
    model : PreTrainedModel
        The model to use for inference.
    contents : bytes
        Image contents.

    Returns
    -------
    tuple[str, float]
        The predicted classification label and its confidence score.
    """

    image = Image.open(io.BytesIO(contents))
    inputs = processor(image, return_tensors="pt")

    with torch.no_grad():
        logits = model(**inputs).logits

    probabilities = torch.softmax(logits, dim=-1)
    predicted_id = int(probabilities.argmax(-1).item())
    id2label = {int(key): value for key, value in (model.config.id2label or {}).items()}
    predicted_label = id2label[predicted_id]
    confidence = probabilities[0, predicted_id].item()

    return predicted_label, confidence


def load_model(path: str) -> tuple[BaseImageProcessor, PreTrainedModel]:
    """
    Load the image processor and classifier.

    Parameters
    ----------
    path : str
        Path to the local model artifacts.

    Returns
    -------
    tuple[BaseImageProcessor, PreTrainedModel]
        The image processor and classifier.
    """
    processor = AutoImageProcessor.from_pretrained(path)
    model = AutoModelForImageClassification.from_pretrained(path)

    return processor, model


@cache
def get_openai_client() -> OpenAI:
    """
    Build the OpenAI client on first use, and reuse it thereafter.

    Constructed lazily rather than at import time: `OpenAI()` raises when
    `OPENAI_API_KEY` is unset, and a missing key shouldn't stop the app (or
    the test suite) from starting, since descriptions are best-effort.

    Returns
    -------
    OpenAI
        The process-wide OpenAI client.
    """
    return OpenAI(timeout=OPENAI_TIMEOUT_S, max_retries=OPENAI_MAX_RETRIES)


def _encode_for_description(contents: bytes) -> str:
    """
    Downscale an image and base64-encode it as JPEG for the vision model.

    Parameters
    ----------
    contents : bytes
        Contents of the original image file.

    Returns
    -------
    str
        Base64-encoded JPEG bytes, ready to embed in a `data:` URL.
    """

    with Image.open(io.BytesIO(contents)) as img:

        # the model sees the image the right way up, the way a browser would
        image = ImageOps.exif_transpose(img) or img
        image = image.convert("RGB")
        image.thumbnail(
            (DESCRIPTION_MAX_PX, DESCRIPTION_MAX_PX),
            Image.Resampling.LANCZOS,
        )

        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=DESCRIPTION_QUALITY)

    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def describe_image(contents: bytes) -> Description:
    """
    Prompt an OpenAI LLM to describe an image.

    Parameters
    ----------
    contents : bytes
        Contents of the image file, in any format Pillow can open.

    Returns
    -------
    Description
        The model's description of the image, its token usage, and the model
        that wrote it.
    """

    image_data = _encode_for_description(contents)

    prompt: ResponseInputParam = [
        {
            "role": "user",
            "content": [
                {
                    "type": "input_text",
                    "text": (
                        "Provide a witty, funny description of the dog "
                        "in this image. Keep it short and sweet, one sentence. "
                        "Plain text only."
                    ),
                },
                {
                    "type": "input_image",
                    "image_url": f"data:image/jpeg;base64,{image_data}",
                    "detail": "auto",
                },
            ],
        }
    ]

    response = get_openai_client().responses.create(
        model=OPENAI_MODEL,
        input=prompt,
    )

    if response.usage is None:
        raise RuntimeError("OpenAI response did not include token usage.")

    return Description(
        description=response.output_text.strip(),
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
        model=response.model,
    )
