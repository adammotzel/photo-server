# Classifier Setup

The app uses the `efficientnet-b0` model to accept only images of dogs.

## Fine-tuning

`scripts/models/finetune.py` replaces the classifier head with a 2-class linear layer ("dog" / "not dog") and trains just that head. The positive class is photos of my dog, the negative class is other photos from my camera roll. (Relabeling ImageNet's dog-breed classes to "dog" without training gave too many false negatives.)

The base and fine-tuned models are not committed to the repo.

## Serving

`finetune.py` writes the model artifacts to `models/`. The app loads them from there at startup.

See [CLASSIFIER.md](../architecture/CLASSIFIER.md) for design notes.
