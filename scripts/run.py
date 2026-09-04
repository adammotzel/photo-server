import os
from pathlib import Path

import uvicorn
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

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
