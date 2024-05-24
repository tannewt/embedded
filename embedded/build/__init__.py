import asyncio
import inspect
import logging
import pathlib
import shlex
import time
import atexit
import json

logger = logging.getLogger(__name__)

shared_semaphore = None

trace_entries = []
def save_trace():
    with open("trace.json", "w") as f:
        json.dump(trace_entries, f)

atexit.register(save_trace)

def init(job_count=1):
    global shared_semaphore
    shared_semaphore = asyncio.BoundedSemaphore(job_count)

    global tracks
    tracks = list(reversed(range(job_count)))

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
        track = tracks.pop()
        start_time = time.perf_counter_ns() // 1000
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=working_directory)

        stdout, stderr = await process.communicate()
        end_time = time.perf_counter_ns() // 1000
        trace_entries.append({"name": command if not description else description, "ph": "X", "pid": 0, "tid": track, "ts": start_time, "dur": end_time - start_time})
        tracks.append(track)

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

async def run_function(function, positional, named, description=None,):
    async with shared_semaphore:
        track = tracks.pop()
        start_time = time.perf_counter_ns() // 1000
        result = await asyncio.to_thread(function, *positional, **named)

        end_time = time.perf_counter_ns() // 1000
        trace_entries.append({"name": str(function) if not description else description, "ph": "X", "pid": 0, "tid": track, "ts": start_time, "dur": end_time - start_time})
        tracks.append(track)

    if description:
        logger.info(description)
        logger.debug(function)
    else:
        logger.info(function)
    return result

def run_in_thread(function):
    def wrapper(*positional, **named):
        return run_function(function, positional, named)
    return wrapper
