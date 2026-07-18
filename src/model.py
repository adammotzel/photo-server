import io

import torch
from PIL import Image

from src.config import model, processor


def inference(contents: bytes) -> str:
    """
    Check if an image contains a dog.

    Parameters
    ----------
    contents : bytes
        Image contents.

    Returns
    -------
    str
        The predicted classification label.
    """

    image = Image.open(io.BytesIO(contents))
    inputs = processor(image, return_tensors="pt")

    with torch.no_grad():
        logits = model(**inputs).logits

    predicted_id = logits.argmax(-1).item()
    predicted_label = model.config.id2label[predicted_id]

    return predicted_label
