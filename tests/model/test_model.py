from pathlib import Path

import pytest

from src.model import inference, load_model

MODEL_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "models" / "efficientnet-b0-dog-classifier"
)


@pytest.fixture(scope="module")
def processor_and_model():
    """
    Load the real processor/classifier once for the whole module.

    Returns
    -------
    tuple[AutoImageProcessor, AutoModelForImageClassification]
        The image processor and classifier loaded from `MODEL_PATH`.
    """
    return load_model(str(MODEL_PATH))


def test_inference_returns_expected_types(processor_and_model, sample_image_bytes):
    """
    Verify `inference` returns a `(str, float)` label/confidence pair.

    Parameters
    ----------
    processor_and_model : tuple
        The image processor and classifier.
    sample_image_bytes : bytes
        Bytes of a real image to classify.
    """
    processor, model = processor_and_model
    label, confidence = inference(processor, model, sample_image_bytes)

    assert isinstance(label, str)
    assert isinstance(confidence, float)


def test_inference_confidence_in_valid_range(processor_and_model, sample_image_bytes):
    """
    Verify `inference`'s confidence score falls within `[0.0, 1.0]`.

    Parameters
    ----------
    processor_and_model : tuple
        The image processor and classifier.
    sample_image_bytes : bytes
        Bytes of a real image to classify.
    """
    processor, model = processor_and_model
    _, confidence = inference(processor, model, sample_image_bytes)

    assert 0.0 <= confidence <= 1.0


def test_inference_label_is_known_class(processor_and_model, sample_image_bytes):
    """
    Verify `inference` returns a label from the model's known class set.

    Parameters
    ----------
    processor_and_model : tuple
        The image processor and classifier.
    sample_image_bytes : bytes
        Bytes of a real image to classify.
    """
    processor, model = processor_and_model
    label, _ = inference(processor, model, sample_image_bytes)

    assert label in model.config.id2label.values()
