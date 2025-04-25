# Photo Album Server

A quick side project to serve photos of my dog on a web app to anyone connected to my home Wi-Fi. The code uses:

- `fastapi` for serving the app.
- `html` for webpages (thanks ChatGPT 🙂).
- `starlette` for middleware (e.g., login/password).

To run the app yourself, follow these steps:

1. Clone the repo:

```bash
git clone https://github.com/adammotzel/photo-album-server.git
cd photo-album-server
```

2. Create a `.env` file in project root:

    1. `PW`: The app's login password.
    2. `UN`: Comma-separated list of acceptable user names.
    3. `NAME`: The name of your pet, to be injected into the HTML templates.
    4. `PYTHONPATH`: Absolute path to the project.
    5. `SECRET`: The key used for the middleware.

```bash
PW=password
UN='john,jane'
NAME='Scooby-doo'
PYTHONPATH=/absolute/path/to/your/project
SECRET=somesupersecretkey
```

3. Set up a virtual environment (I used Python `3.12.8`):

```bash
python -m venv venv
source venv/Scripts/activate
```

4. Install requirements:

```bash
pip install -r requirements.txt
```

5. Run the app:

```bash
python main.py
```

The app will launch on host `0.0.0.0` (all available network interfaces) and port `8000` by default. You can change this in the `main.py` file.

If you want to serve the app to other devices connected to your home Wi-Fi (like I did), you may need to allow inbound traffic on the port for private networks. This can be configured in your machine's firewall settings.

Other in-network devices can access the app at `<local IP address>:<port>`. You can try setting the local domain to something more user-friendly, if you'd like.
