"""
Fine-tune efficientnet-b0 into a real dog / not-dog binary classifier.

Replaces the 1000-class ImageNet head with a 2-class linear layer and
trains only that head (linear probe) on:

    - `src/photos/*`     -> label "dog"
    - `data/training/*`  -> label "not dog"

```python
python -m scripts.models.finetune
```

The base model in `models/efficientnet-b0` is left untouched. The fine-tuned
model is saved to `models/efficientnet-b0-dog-classifier`.
"""

import random
from pathlib import Path

import torch
from PIL import Image
from torch import nn
from torch.utils.data import DataLoader, Dataset
from torchvision import transforms
from transformers import AutoImageProcessor, AutoModelForImageClassification

BASE_MODEL_PATH = "models/efficientnet-b0"
OUTPUT_MODEL_PATH = "models/efficientnet-b0-dog-classifier"

DOG_DIR = Path("src/photos")
NOT_DOG_DIR = Path("data/training")
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}

ID2LABEL = {0: "not dog", 1: "dog"}
LABEL2ID = {"not dog": 0, "dog": 1}

VAL_FRACTION = 0.2
SEED = 42
BATCH_SIZE = 8
MAX_EPOCHS = 30
LEARNING_RATE = 1e-3
WEIGHT_DECAY = 1e-4
EARLY_STOPPING_PATIENCE = 5

TRAIN_AUGMENTATION = transforms.Compose(
    [
        transforms.RandomHorizontalFlip(),
        transforms.RandomRotation(15),
        transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2),
    ]
)


class DogDataset(Dataset):
    """Loads (image, label) pairs and applies the model's own processor."""

    def __init__(
        self,
        samples: list[tuple[Path, int]],
        processor,
        augment: bool,
    ):
        self.samples = samples
        self.processor = processor
        self.augment = augment

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, int]:
        path, label = self.samples[idx]
        image = Image.open(path).convert("RGB")
        if self.augment:
            image = TRAIN_AUGMENTATION(image)
        pixel_values = self.processor(image, return_tensors="pt")["pixel_values"][0]
        return pixel_values, label


def list_images(directory: Path) -> list[Path]:
    return sorted(p for p in directory.iterdir() if p.suffix.lower() in IMAGE_EXTENSIONS)


def stratified_split(
    paths: list[Path], label: int, val_fraction: float, rng: random.Random
) -> tuple[list[tuple[Path, int]], list[tuple[Path, int]]]:
    shuffled = paths[:]
    rng.shuffle(shuffled)
    n_val = max(1, round(len(shuffled) * val_fraction))
    val = [(p, label) for p in shuffled[:n_val]]
    train = [(p, label) for p in shuffled[n_val:]]
    return train, val


def build_splits() -> tuple[list[tuple[Path, int]], list[tuple[Path, int]]]:
    dog_paths = list_images(DOG_DIR)
    not_dog_paths = list_images(NOT_DOG_DIR)

    if not dog_paths:
        raise RuntimeError(f"No images found in {DOG_DIR}")
    if not not_dog_paths:
        raise RuntimeError(
            f"No images found in {NOT_DOG_DIR}. Add some 'not dog' photos there first."
        )

    rng = random.Random(SEED)
    dog_train, dog_val = stratified_split(dog_paths, LABEL2ID["dog"], VAL_FRACTION, rng)
    not_dog_train, not_dog_val = stratified_split(
        not_dog_paths, LABEL2ID["not dog"], VAL_FRACTION, rng
    )

    train_samples = dog_train + not_dog_train
    val_samples = dog_val + not_dog_val
    rng.shuffle(train_samples)
    rng.shuffle(val_samples)

    print(
        f"dog: {len(dog_paths)} images ({len(dog_train)} train / {len(dog_val)} val), "
        f"not dog: {len(not_dog_paths)} images ({len(not_dog_train)} train / {len(not_dog_val)} val)"
    )

    return train_samples, val_samples


def class_weights(train_samples: list[tuple[Path, int]]) -> torch.Tensor:
    counts = [0, 0]
    for _, label in train_samples:
        counts[label] += 1
    total = sum(counts)
    weights = [total / (2 * count) if count else 0.0 for count in counts]
    return torch.tensor(weights, dtype=torch.float32)


def freeze_backbone(model) -> None:
    for param in model.efficientnet.parameters():
        param.requires_grad = False
    model.efficientnet.eval()


def set_train_mode(model) -> None:
    model.classifier.train()
    model.dropout.train()
    model.efficientnet.eval()  # keep frozen backbone's BatchNorm stats from drifting


@torch.no_grad()
def evaluate(model, loader: DataLoader) -> float:
    model.eval()
    correct = 0
    total = 0
    for pixel_values, labels in loader:
        logits = model(pixel_values=pixel_values).logits
        preds = logits.argmax(-1)
        correct += (preds == labels).sum().item()
        total += len(labels)
    return correct / total


def main() -> None:
    train_samples, val_samples = build_splits()

    processor = AutoImageProcessor.from_pretrained(BASE_MODEL_PATH)
    model = AutoModelForImageClassification.from_pretrained(
        BASE_MODEL_PATH,
        num_labels=2,
        id2label=ID2LABEL,
        label2id=LABEL2ID,
        ignore_mismatched_sizes=True,
    )
    freeze_backbone(model)

    train_loader = DataLoader(
        DogDataset(train_samples, processor, augment=True),
        batch_size=BATCH_SIZE,
        shuffle=True,
    )
    val_loader = DataLoader(
        DogDataset(val_samples, processor, augment=False),
        batch_size=BATCH_SIZE,
        shuffle=False,
    )

    loss_fn = nn.CrossEntropyLoss(weight=class_weights(train_samples))
    optimizer = torch.optim.AdamW(
        model.classifier.parameters(), lr=LEARNING_RATE, weight_decay=WEIGHT_DECAY
    )

    best_val_acc = -1.0
    best_state = None
    epochs_without_improvement = 0

    for epoch in range(MAX_EPOCHS):
        set_train_mode(model)
        running_loss = 0.0

        for pixel_values, labels in train_loader:
            optimizer.zero_grad()
            logits = model(pixel_values=pixel_values).logits
            loss = loss_fn(logits, labels)
            loss.backward()
            optimizer.step()
            running_loss += loss.item() * len(labels)

        val_acc = evaluate(model, val_loader)
        print(
            f"epoch {epoch + 1}/{MAX_EPOCHS}: "
            f"train_loss={running_loss / len(train_samples):.4f} val_acc={val_acc:.4f}"
        )

        if val_acc > best_val_acc:
            best_val_acc = val_acc
            best_state = {k: v.clone() for k, v in model.classifier.state_dict().items()}
            epochs_without_improvement = 0
        else:
            epochs_without_improvement += 1
            if epochs_without_improvement >= EARLY_STOPPING_PATIENCE:
                print("Early stopping.")
                break

    model.classifier.load_state_dict(best_state)
    model.save_pretrained(OUTPUT_MODEL_PATH)
    processor.save_pretrained(OUTPUT_MODEL_PATH)

    print(f"Best val accuracy: {best_val_acc:.4f}")
    print(f"Saved fine-tuned model to {OUTPUT_MODEL_PATH}")


if __name__ == "__main__":
    main()
