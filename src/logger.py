import logging
import queue
from logging.handlers import QueueHandler, QueueListener

q = queue.Queue(-1)
qh = QueueHandler(q)
handler = logging.StreamHandler()
listener = QueueListener(q, handler)
logger = logging.getLogger()
logger.addHandler(qh)
logger.setLevel(logging.INFO)
formatter = logging.Formatter(
    "%(threadName)s | %(asctime)s | %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H-%M-%S",
)
handler.setFormatter(formatter)
