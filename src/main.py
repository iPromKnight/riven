import contextlib
import signal
import sys
import threading
import asyncio
import time
import traceback

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from controllers.actions import router as actions_router
from controllers.default import router as default_router
from controllers.items import router as items_router
from controllers.settings import router as settings_router
from controllers.tmdb import router as tmdb_router
from controllers.webhooks import router as webhooks_router
from controllers.ws import router as ws_router
from program.riven import RivenTemporalWorker
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from utils.cli import handle_args
from utils.logger import logger

class LoguruMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        response = None
        try:
            response = await call_next(request)
        except Exception as e:
            logger.exception(f"Exception during request processing: {e}")
            raise
        finally:
            process_time = time.time() - start_time
            status_code = response.status_code if response else 500
            logger.log(
                "API",
                f"{request.method} {request.url.path} - {status_code} - {process_time:.2f}s",
            )
        return response


args = handle_args()

app = FastAPI(
    title="Riven",
    summary="A media management system.",
    version="0.7.x",
    redoc_url=None,
    license_info={
        "name": "GPL-3.0",
        "url": "https://www.gnu.org/licenses/gpl-3.0.en.html",
    },
)
app.riven = RivenTemporalWorker()

app.add_middleware(LoguruMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(default_router)
app.include_router(settings_router)
app.include_router(items_router)
app.include_router(webhooks_router)
app.include_router(tmdb_router)
app.include_router(actions_router)
app.include_router(ws_router)

class Server(uvicorn.Server):
    def install_signal_handlers(self):
        pass

    @contextlib.contextmanager
    def run_in_thread(self):
        thread = threading.Thread(target=self.run, name="Riven")
        thread.start()
        try:
            while not self.started:
                time.sleep(1e-3)
            yield
        except Exception as e:
            logger.error(f"Error in server thread: {e}")
            logger.exception(traceback.format_exc())
            raise e
        finally:
            self.should_exit = True
            sys.exit(0)

async def start_riven():
    """Start the Riven worker asynchronously."""
    await app.riven.start()
    await app.riven.worker.run()  # Assuming `run()` is also an async method

async def shutdown():
    """Handle the shutdown of both Uvicorn and the Riven worker."""
    logger.log("PROGRAM", "Initiating shutdown sequence...")
    await app.riven.stop()
    logger.log("PROGRAM", "Riven worker stopped. Now shutting down Uvicorn...")
    # Here, we ensure Uvicorn will stop by signaling to its `should_exit` flag
    server.should_exit = True

def signal_handler(signum, frame):
    logger.log("PROGRAM", "Exiting Gracefully.")
    loop = asyncio.get_event_loop()
    asyncio.run_coroutine_threadsafe(shutdown(), loop)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

config = uvicorn.Config(app, host="0.0.0.0", port=8080, log_config=None)
server = Server(config=config)

with server.run_in_thread():
    try:
        asyncio.run(start_riven())  # Run the Riven worker in the event loop
    except Exception as e:
        logger.error(f"Error in main thread: {e}")
        logger.exception(traceback.format_exc())
    finally:
        logger.critical("Server has been stopped")
        sys.exit(0)