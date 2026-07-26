from pathlib import Path

from src.model import inference, model


def test_inference_returns_expected_types(sample_image_bytes):
    """
    Verify `inference` returns a `(str, float)` label/confidence pair.

    Parameters
    ----------
    sample_image_bytes : bytes
        Bytes of a real image to classify.
    """
    label, confidence = inference(sample_image_bytes)

    assert isinstance(label, str)
    assert isinstance(confidence, float)


def test_inference_confidence_in_valid_range(sample_image_bytes):
    """
    Verify `inference`'s confidence score falls within `[0.0, 1.0]`.

    Parameters
    ----------
    sample_image_bytes : bytes
        Bytes of a real image to classify.
    """
    _, confidence = inference(sample_image_bytes)

    assert 0.0 <= confidence <= 1.0


def test_inference_label_is_known_class(sample_image_bytes):
    """
    Verify `inference` returns a label from the model's known class set.

    Parameters
    ----------
    sample_image_bytes : bytes
        Bytes of a real image to classify.
    """
    label, _ = inference(sample_image_bytes)

    assert label in model.config.id2label.values()
