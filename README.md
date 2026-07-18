# Photo Server

A quick side project to serve photos of my dog on a web app to anyone connected to my home Wi-Fi. The app uses:

- `fastapi` for serving the app.
- `html` for some vanilla webpages.
- `starlette` for middleware.
- PostgreSQL as the backend database.

## App Features

- User registration + login for auth (not really necessary for a simple app like this, but useful for tracking photo metadata)
- Ability for users to upload new photos
- Ability for users to view all uploaded photos in a "gallery"

I've also added an image verification layer that employs the `efficientnet-b0` vision model to only allow images of dogs to be uploaded to the app. I downloaded the model locally (using `scripts/models/download.py`) then manually changed the labels of all dog breeds to "dog" in the model config. Pretty lazy, but it's a simple approach to effectively making it a binary classifier ("dog" vs. "not dog"). We'll see how it works out; maybe I'll need to fine-tune the model a bit.

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
    2. `SECRET`: Absolute path to the project.
    3. `POSTGRES_PW`: Your app's Postgres user password.

```bash
NAME='Scooby-doo'
SECRET='somesupersecretkey'
POSTGRES_PW='anothersupersecretkey'
```

You can generate a good secret for the middleware like this:
```python
import secrets

secret = secrets.token_urlsafe(64)
print(secret)
```
It's not required, but it's a good practice.

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

#### 7. Update the classifier config

Update the classifier's `config.json` file so that all dog breeds have the label 'dog'. I left a copy of the edited `id2label` property in `docs/CLASSIFIER-CONFIG.md` so you can just copy it over.

If your pet is not a dog, you'll have to edit the config accordingly.

#### 8. Run the app from the project root directory

```bash
python -m scripts.run
```

#### 9. Create a new user for the app

You'll need to register a user to log into the app. Registered usernames and passwords are used for authentication and photo metadata.

When you launch the app, click the "register" button and fill out the form. The user's credentials will be stored in the Postgres database for future authentication.

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

Postgres is simple to set up and use. It's only used for storing registered user credentials (usernames and hashed passwords) and uploaded photo metadata. The photos themselves are just stored on disk.

I chose to use `psycopg` for database interactions. It's lighter and faster than an ORM like SQLAlchemy, and since I only have two database tables, an ORM felt like overkill.

### Image Verification Layer

Google's `efficientnet-b0` vision model offers solid accuracy and low resource consumption. It works great for a small app served on CPU.
