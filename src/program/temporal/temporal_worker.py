import asyncio
import subprocess
import threading
import time
import program.temporal.literals as literals
from temporalio.client import Client

from program.temporal.payload_converter import pydantic_data_converter
from program.temporal.schedules import RivenWorkflowSchedules
from program.temporal.service_container import ServiceContainer
from temporalio.worker import Worker
from program.temporal.retries import RetriesWorkflow, RetriesActivity
from program.temporal.mediaitems import MediaItemWorkflow
from program.temporal.mediaitems import (
    HandleRequestedOrUnknown,
    HandleIndexedOrPartiallyCompleted,
    HandleScraped,
    HandleDownloaded,
    HandleSymlinked,
    HandleCompleted
)
from utils.logger import logger


def start_temporal_server():
    process = subprocess.Popen(
        [
            "temporal",
            "server",
            "start-dev",
            "--log-level", "never",
            "--ip=0.0.0.0",
            f"--namespace={literals.TEMPORAL_NAMESPACE}"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    def log_stdout():
        for line in iter(process.stdout.readline, ""):
            logger.info(line.strip())

    def log_stderr():
        for line in iter(process.stderr.readline, ""):
            logger.error(line.strip())

    threading.Thread(target=log_stdout, daemon=True).start()
    threading.Thread(target=log_stderr, daemon=True).start()

    logger.info("Temporal server started successfully.")
    return process


async def wait_for_temporal_server(timeout=10, interval=1):
    start_time = time.time()
    while True:
        try:
            client = await Client.connect(
                target_host=f"{literals.TEMPORAL_HOST}:{literals.TEMPORAL_PORT}",
                namespace=literals.TEMPORAL_NAMESPACE,
                data_converter=pydantic_data_converter)
            logger.info("Connected to Temporal server successfully.")
            return client
        except Exception as e:
            if time.time() - start_time > timeout:
                logger.error(f"Timed out waiting for Temporal server to start: {e}")
                exit(1)
            await asyncio.sleep(interval)


class RivenTemporalWorker:
    def __init__(self):
        self.worker = None
        self.process = None
        self.container = ServiceContainer()

    async def create_worker(self):
        self.container.wire(modules=[__name__])
        # container_valid = self.container.check_dependencies()
        # if not container_valid:
        #     logger.error("Service container failed to initialize.")
        #     exit(1)

        client = await wait_for_temporal_server()
        self.container.temporal_client.init()

        schedules = RivenWorkflowSchedules(client)
        await schedules.create_schedules()

        self.worker = Worker(
            client,
            task_queue=literals.TASK_QUEUE,
            workflows=[
                RetriesWorkflow,
                MediaItemWorkflow
            ],
            activities=[
                HandleRequestedOrUnknown(),
                HandleIndexedOrPartiallyCompleted(),
                HandleScraped(),
                HandleDownloaded(),
                HandleSymlinked(),
                HandleCompleted(),
                RetriesActivity(),
            ],
        )

        logger.info("Worker created successfully.")

    async def start(self):
        if not self.process:
            self.process = start_temporal_server()
        if not self.worker:
            await self.create_worker()
        await self.worker.run()

    async def stop(self):
        if self.worker:
            await self.worker.shutdown()
        if self.process:
            self.process.terminate()