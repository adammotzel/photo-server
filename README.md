# Photo Server

A quick side project to serve photos of my dog on a web app to anyone connected to my home Wi-Fi. The app uses:

- `fastapi` for serving the app.
- `html` for some vanilla webpages.
- PostgreSQL as the backend database.

## App Features

- Open access on your home Wi-Fi, no accounts or login required
- Ability for users to upload new photos, automatically attributed to the uploading device's LAN IP address (for tracking photo metadata; no user action needed)
- Ability for users to view all uploaded photos in a "gallery"

I've also added an image verification layer that employs the `efficientnet-b0` vision model to only allow images of dogs to be uploaded to the app. I downloaded the model locally (using `scripts/models/download.py`). My first pass was pretty lazy: I just relabeled all ImageNet dog-breed classes to "dog" in the model config and left the other 1000-way head in place. That produced a lot of false negatives, so I decided to fine-tune it. 

`scripts/models/finetune.py` replaces the classifier head with a real 2-class linear layer ("dog" / "not dog") and trains just that head (backbone frozen) on my own photos of my dog (`src/photos/`) plus a folder of "not dog" photos I collected (`data/training/`). The results are promising.

> NOTE: The efficientnet-b0 model and my fine-tuned model are not commited to the repository.

## Setup and Usage

To run the app yourself, follow these steps:

#### 1. Clone the repo

```bash
git clone https://github.com/adammotzel/photo-server.git
cd photo-server
```

#### 2. Set up the PostreSQL database

Follow the instructions in `docs/POSTGRES-SETUP.md`.

#### 3. Create a `src/.env` file

    1. `NAME`: The name of your pet, to be injected into the HTML templates.
    2. `POSTGRES_PW`: Your app's Postgres user password.

```bash
NAME='Scooby-doo'
POSTGRES_PW='anothersupersecretkey'
```

#### 4. Set up a virtual environment 

Create the environment using `uv`. If you don't have `uv`, you can install it [here](https://docs.astral.sh/uv/getting-started/installation/)).

```bash
uv venv
```

#### 5. Activate the virtual env and install dependencies

```bash
source .venv/Scripts/activate || source .venv/bin/activate
uv sync
```

#### 6. Download the image classification model

```bash
python scripts/models/download.py
```

#### 7. Fine-tune the classifier for your pet

Add some photos of your pet to `src/photos/` (these double as upload examples and as the "positive" class for fine-tuning), then add a folder of "not your pet" photos at `data/training/`; people, rooms, outdoor scenes, whatever your app might realistically see. Roughly matching the count of your pet's photos, with some variety, works well.

Then run:

```bash
python -m scripts.models.finetune
```

This replaces the classifier's head with a real 2-class linear layer and trains just that head (the rest of the model stays frozen), saving the result to `models/efficientnet-b0-dog-classifier`. `src/config.py` already points there.

If you'd rather skip fine-tuning, `docs/CLASSIFIER-CONFIG.md` documents the original (much lazier, more false-negative-prone) approach of just relabeling ImageNet classes in the base model's config.

#### 8. Run the app from the project root directory

```bash
python -m scripts.run
```

### Notes

The app will launch on host `0.0.0.0` and port `8000` by default. You can change this in `scripts/run.py`.

If you want to serve the app to other devices connected to your home Wi-Fi, you may need to allow inbound traffic on the port for private networks. This can be configured in your machine's firewall settings.

Other in-network devices can access the app at `<local IP address>:<port>`. You can try setting the local domain to something more user-friendly, if you'd like.

## Architecture Decisions

### FastAPI Backend

FastAPI is my default Python web framework. It's just really easy to use.

The endpoints are defined as async, but all core app functions are written synchronously. I use FastAPI's `run_in_threadpool` utility to offload blocking operations to worker threads. It works well for an app of this size.

### HTML Frontend

It's a simple app, and HTML works fine for serving static web pages. Maybe someday I'll implement a heavier frontend framework for fun.

### PostgreSQL Database Backend

Postgres is simple to set up and use. It's only utilized for storing uploaded photo metadata, including the uploading device's LAN IP address, and the classifier's predictions. The photos themselves are just stored on disk.

I chose to use `psycopg` for database interactions. It's lighter and faster than an ORM like SQLAlchemy, and since I only have two database tables, an ORM felt like overkill.

### Image Verification Layer

Google's `efficientnet-b0` vision model offers solid accuracy and low resource consumption. It works great for a small app served on CPU.
