import io

import torch
from PIL import Image
from transformers import AutoImageProcessor, AutoModelForImageClassification
from transformers.image_processing_utils import BaseImageProcessor
from transformers.modeling_utils import PreTrainedModel


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
