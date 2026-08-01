# Classifier Setup

I employ the `efficientnet-b0` vision model to only allow images of dogs to be uploaded to the app. 

## Finetuning

My first pass was pretty lazy: I downloaded the model locally then relabeled all ImageNet dog-breed classes to "dog" in the model config and left all other classes in place. That approach ended up producing a lot of false negatives, so I decided to fine-tune the model.

The `scripts/models/finetune.py` script replaces the classifier head with a real 2-class linear layer ("dog" / "not dog") and trains just that head on "dog" photos (my dog) and "not dog" photos I collected.

> NOTE: The base efficientnet-b0 model and my fine-tuned version are not commited to the repository.

I used photos of my dog as the "positive" class, and other random photos from my camera roll as the "negative" class.
