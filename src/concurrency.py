import asyncio

from src.config import BLOCKING_EXECUTOR


async def run_blocking(func, *args, **kwargs):
    """Offload blocking operations to worker threadpool."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        BLOCKING_EXECUTOR,
        lambda: func(*args, **kwargs),
    )
