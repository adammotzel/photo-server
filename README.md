# Photo Server

A quick side project to serve photos of my dog on a web app to anyone connected to my home Wi-Fi. The app uses:

- `fastapi` for serving the app.
- `html` for some vanilla webpages.
- `starlette` for middleware.
- PostgreSQL as the backend database.

Users can view and upload photos in the app's photo gallery.

## Setup and Usage
To run the app yourself, follow these steps:

#### 1. Clone the repo:

```bash
git clone https://github.com/adammotzel/photo-server.git
cd photo-server
```

#### 2. Follow the instructions in `docs/POSTGRES-SETUP.md` to set up the PostreSQL database.

#### 3. Create a `src/.env` file:

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

#### 4. Set up a virtual environment using `uv` (if you don't have `uv`, you can install it [here](https://docs.astral.sh/uv/getting-started/installation/)):

```bash
uv venv
```

#### 5. Activate the virtual env and install dependencies:

```bash
source .venv/Scripts/activate || source .venv/bin/activate
uv sync
```

#### 6. Run the app from the project root directory:

```bash
python -m scripts.run
```

#### 7. Create a new user for the app

You'll need to register a user to log into the app. Registered usernames and passwords are used for authentication.

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
