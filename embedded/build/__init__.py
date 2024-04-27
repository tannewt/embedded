import asyncio
import inspect
import logging
import pathlib
import shlex

logger = logging.getLogger(__name__)

shared_semaphore = None

def init(job_count=1):
    global shared_semaphore
    shared_semaphore = asyncio.BoundedSemaphore(job_count)

async def run_command(command, description=None, working_directory=None):
    if isinstance(command, list):
        for i, part in enumerate(command):
            if isinstance(part, pathlib.Path):
                part = part.relative_to(working_directory, walk_up=True)
            command[i] = str(part)
        command = " ".join(command)

    if working_directory is None:
        caller_frame = inspect.stack()[1].filename
        working_directory = pathlib.Path(caller_frame).parent
    async with shared_semaphore:
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=working_directory)

    stdout, stderr = await process.communicate()

    working_directory = working_directory.relative_to(pathlib.Path.cwd())
    command = f"{working_directory}$ {command}"

    if process.returncode == 0:
        logger.info(command)
    else:
        if stdout:
            logger.info(stdout.decode("utf-8").strip())
        if stderr:
            logger.warning(stderr.decode("utf-8").strip())
        logger.error(command)
