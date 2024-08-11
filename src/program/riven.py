import asyncio
import os
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from program.settings.manager import settings_manager
from program.settings.models import get_version
from program.temporal.orchestration import create_schedules
from program.temporal.service_container import ServiceContainer
import program.temporal.orchestration.shared as shared
from temporalio.client import Client
from program.db.db import run_migrations
from temporalio.worker import Worker

from utils import data_dir_path
from utils.logger import logger, scrub_logs
from program.temporal.retries import retries_activities, RetriesWorkflow
from program.temporal.overseer import overseerr_activities, OverseerrWorkflow
from program.temporal.mediaitems import media_item_activities, MediaItemWorkflow


class RivenTemporalWorker:
    def __init__(self):
        self.worker: Optional[Worker] = None
        self.process: Optional[subprocess.Popen] = None
        self.container: Optional[ServiceContainer] = None

    @staticmethod
    async def wait_for_temporal_server(timeout=10, interval=1):
        start_time = time.time()
        while True:
            try:
                client = await Client.connect(
                    target_host=f"{shared.TEMPORAL_HOST}:{shared.TEMPORAL_PORT}",
                    namespace=shared.TEMPORAL_NAMESPACE)
                logger.debug("Connected to Temporal server successfully.")
                return client
            except Exception as e:
                if time.time() - start_time > timeout:
                    logger.error(f"Timed out waiting for Temporal server to start: {e}")
                    exit(1)
                await asyncio.sleep(interval)

    @staticmethod
    def start_temporal_server():
        process = subprocess.Popen(
            [
                "temporal",
                "server",
                "start-dev",
                "--log-level", "never",
                "--ip=0.0.0.0",
                f"--namespace={shared.TEMPORAL_NAMESPACE}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,
        )

        def temporal_server_stdout():
            for line in iter(process.stdout.readline, ""):
                logger.debug(line.strip())

        def temporal_server_stderr():
            for line in iter(process.stderr.readline, ""):
                logger.error(line.strip())

        threading.Thread(target=temporal_server_stdout, daemon=True).start()
        threading.Thread(target=temporal_server_stderr, daemon=True).start()

        logger.log("PROGRAM", "Temporal server started successfully.")
        return process

    async def create_worker(self):
        client = await self.wait_for_temporal_server()
        self.worker = Worker(
            client,
            task_queue=shared.TASK_QUEUE,
            workflows=[
                MediaItemWorkflow,
                RetriesWorkflow,
                OverseerrWorkflow,
            ],
            activities=[
                *retries_activities(),
                *overseerr_activities(),
                *media_item_activities(),
            ],
            activity_executor=ThreadPoolExecutor(max_workers=100),
            max_cached_workflows=10,
            max_concurrent_workflow_tasks=10,
        )

        # Prom. do this here, as it injects a temporal client and needs the service running to connect =)
        if not self.container:
            await self.setup_container()

        await create_schedules(client)

        logger.debug("Worker created successfully.")

    async def start(self):
        latest_version = get_version()
        logger.log("PROGRAM", f"Riven v{latest_version} starting!")
        os.makedirs(data_dir_path, exist_ok=True)
        if not settings_manager.settings_file.exists():
            logger.log("PROGRAM", "Settings file not found, creating default settings")
            settings_manager.save()
        scrub_logs()
        max_worker_env_vars = [var for var in os.environ if var.endswith("_MAX_WORKERS")]
        if max_worker_env_vars:
            for var in max_worker_env_vars:
                logger.log("PROGRAM", f"{var} is set to {os.environ[var]} workers")
        run_migrations()
        if not self.process:
            self.process = self.start_temporal_server()
        if not self.worker:
            await self.create_worker()
        self.process_meta_data()
        logger.success("Riven is running!")
        await self.worker.run()

    async def stop(self):
        if self.worker:
            logger.debug("Stopping Temporal worker...")
            await self.worker.shutdown()

        if self.process:
            logger.debug("Terminating Temporal server process...")
            self.process.terminate()
            self.process.communicate()
            try:
                self.process.wait(timeout=10)
                logger.debug("Temporal server process terminated.")
            except subprocess.TimeoutExpired:
                logger.warning("Temporal server process did not terminate in time, forcing kill...")
                self.process.kill()
                self.process.wait()
                logger.debug("Temporal server process forcefully terminated.")

    async def setup_container(self):
        try:
            self.container = ServiceContainer()
            await self.container.bootstrap()
        except Exception as e:
            logger.error(f"Error setting up service injection: {e}")
            exit(1)

    @staticmethod
    def process_meta_data():
        from program.db.postgres_repository import PostgresRepository
        PostgresRepository.process_meta_data()