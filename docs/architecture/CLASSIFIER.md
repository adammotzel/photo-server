# Classifier

The classifier's job is to gate uploads: only images predicted as `"dog"` are saved. It's a fine-tuned `efficientnet-b0` model, loaded once at import time in `src/model.py` from `models/efficientnet-b0-dog-classifier`.

## Model

The base `google/efficientnet-b0` model's classifier head is replaced with a 2-class linear layer (`"dog"` / `"not dog"`), and only that head is trained. See [docs/setup/CLASSIFIER.md](../setup/CLASSIFIER.md) for how I run the fine-tuning script and where the training data comes from.

## Inference

`inference()` takes raw image bytes, runs them through the model's processor and forward pass, and returns the predicted label and its confidence score (softmax over the model's logits). It's a synchronous, CPU-bound function, so the upload path (see [UPLOAD](UPLOAD.md)) always calls it through `run_in_threadpool` rather than awaiting it directly.

## Why efficientnet-b0

`efficientnet-b0` is accurate enough for this use case and cheap enough to run on CPU, which matters since the app (usually) just runs from my laptop.
