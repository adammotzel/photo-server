import io
import os

import torch
from PIL import Image
from transformers import AutoImageProcessor, AutoModelForImageClassification

# image classifier
_wd = os.getcwd()
_model_path = f"{_wd}/models/efficientnet-b0-dog-classifier"
processor = AutoImageProcessor.from_pretrained(_model_path)
model = AutoModelForImageClassification.from_pretrained(_model_path)


def inference(contents: bytes) -> tuple[str, float]:
    """
    Check if an image contains a dog.

    Parameters
    ----------
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
    predicted_label = model.config.id2label[predicted_id]
    confidence = probabilities[0, predicted_id].item()

    return predicted_label, confidence
