# Photo Server

A quick side project to serve photos of my dog on a web app to anyone connected to my home Wi-Fi. The app uses:

- `fastapi` for serving the app.
- `html` for some vanilla webpages.
- PostgreSQL as the backend database.

## App Features

- Open access on trusted Wi-Fi networks, no accounts or login required
- Ability for users to upload new photos, automatically attributed to the uploading device's LAN IP address (for tracking photo metadata)
- Ability for users to view all uploaded photos in a "gallery"
- An image verification layer (using the `efficientnet-b0` vision model)

## Architecture Decisions

### FastAPI Backend

FastAPI is my default Python web framework. It's just really easy to use.

The endpoints are defined as async, but most core app functions are written synchronously. I use FastAPI's `run_in_threadpool` utility to offload blocking operations to worker threads. It works well for an app of this size.

### HTML Frontend

It's a simple app, and HTML works fine for serving static web pages. Maybe someday I'll implement a heavier frontend framework for fun.

### PostgreSQL Database Backend

Postgres is simple to set up and use. It's only utilized for storing uploaded photo metadata, including the uploading device's LAN IP address, and the classifier's predictions. The photos themselves are just stored on disk.

I chose to use `psycopg` for database interactions. It's lighter and faster than an ORM like SQLAlchemy, and since I only have three database tables (photos, predictions, and a small networks lookup table), an ORM felt like overkill.

### Image Verification Layer

Google's `efficientnet-b0` vision model offers solid accuracy and low resource consumption. It works great for a small app served on CPU.

## Documentation

See [docs/architecture](docs/architecture) for a deeper architecture breakdown and [docs/setup](docs/setup) for app configuration details.
