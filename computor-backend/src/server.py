import asyncio
import uvicorn
from computor_backend.settings import settings
from computor_backend.server import startup_logic

if __name__ == "__main__":

    if settings.DEBUG_MODE != "production":
        asyncio.run(startup_logic())

    uvicorn.run("computor_backend.server:app", host="0.0.0.0", port=8000, log_level="debug", reload=True, workers=1)
