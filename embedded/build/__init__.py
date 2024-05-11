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


def capture_caller_directory(function):
    def wrapper(*args, **kwargs):
        # Don't override a given caller_directory.
        if "caller_directory" not in kwargs or kwargs["caller_directory"] is None:
            caller_frame = inspect.stack()[1].filename
            caller_directory = pathlib.Path(caller_frame).parent
            kwargs["caller_directory"] = caller_directory

        return function(*args, **kwargs)

    return wrapper

@capture_caller_directory
async def run_command(command, description=None, caller_directory=None, working_directory=None):
    if working_directory is None:
        working_directory = caller_directory
    if isinstance(command, list):
        for i, part in enumerate(command):
            if isinstance(part, pathlib.Path):
                part = part.relative_to(working_directory, walk_up=True)
            # if isinstance(part, list):

            command[i] = str(part)
        command = " ".join(command)

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
        if description:
            logger.info(description)
            logger.debug(command)
        else:
            logger.info(command)
    else:
        if stdout:
            logger.info(stdout.decode("utf-8").strip())
        if stderr:
            logger.warning(stderr.decode("utf-8").strip())
        if not stdout and not stderr:
            logger.warning("No output")
        logger.error(command)
        raise RuntimeError()
