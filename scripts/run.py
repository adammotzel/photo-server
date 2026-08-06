import os

import uvicorn
from dotenv import load_dotenv

load_dotenv(f"{os.getcwd()}/.env")

uvicorn.run(
    "src.app:app", 
    host=os.environ["SERVER_IP"], 
    port=int(os.environ["SERVER_PORT"]), 
    reload=False,
    log_config=None,
    access_log=False,
    ssl_certfile=os.environ["SSL_CERTFILE"],
    ssl_keyfile=os.environ["SSL_KEYFILE"],
    timeout_graceful_shutdown=10,
)
