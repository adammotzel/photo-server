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
    # long enough for in-flight background descriptions to finish (each
    # OpenAI call is bounded by OPENAI_TIMEOUT_S / OPENAI_MAX_RETRIES in
    # src/config.py). Keep below stop_grace_period in compose.yaml, or Docker
    # kills the container first
    timeout_graceful_shutdown=90,
)
