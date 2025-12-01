import os

import uvicorn

uvicorn.run(
    "src.app:app", 
    host=os.getenv("SERVER_IP", "0.0.0.0"), 
    port=os.getenv("SERVER_PORT", 8000), 
    reload=False,
    log_config=None
)
    