import argparse
import asyncio
import colorlog
import inspect
import logging
import os
import pathlib
import sys
import warnings

import embedded
from embedded import build
from embedded import cpu
from embedded import microcontroller

async def run_eager(coro):
    """Run the coroutine with an eager task factory so that functions can capture the parent task."""
    loop = asyncio.get_event_loop()
    loop.set_task_factory(asyncio.eager_task_factory)
    await coro

def run(function):
    function_args = []
    parser = argparse.ArgumentParser()
    parser.add_argument("-j", "--jobs", type=int, help="Number of concurrent jobs to run")
    parser.add_argument(
        '-d', '--debug',
        help="Print lots of debugging statements",
        action="store_const", dest="loglevel", const=logging.DEBUG,
        default=logging.WARNING,
    )
    parser.add_argument(
        '-v', '--verbose',
        help="Be verbose",
        action="store_const", dest="loglevel", const=logging.INFO,
    )

    for param in inspect.signature(function).parameters.values():
        if param.annotation == embedded.CPU:
            cpu_help = "cpu target name"
            parser.add_argument("-c", "--cpu", type=str,
                    help=cpu_help)
            function_args.append("cpu")
        if param.annotation == embedded.CPU or param.annotation == embedded.Microcontroller:
            mcu_help = "mcu target name"
            parser.add_argument("-m", "--mcu", type=str,
                    help=mcu_help)
            if param.annotation == embedded.Microcontroller:
                function_args.append("mcu")

        if param.annotation == pathlib.Path:
            parser.add_argument("--" + param.name, type=pathlib.Path, help="Path to " + param.name, required=param.default == inspect.Parameter.empty)
            function_args.append(param.name)

        if param.annotation == list[str]:
            parser.add_argument(param.name, type=str, nargs="+", help="List of " + param.name)
            function_args.append(param.name)

        #print(param, type(param), param.annotation)

    cli_args = parser.parse_args()

    if not cli_args.jobs:
        cli_args.jobs = os.cpu_count()
    build.init(cli_args.jobs)

    handler = colorlog.StreamHandler()
    handler.setFormatter(colorlog.ColoredFormatter(
        '%(log_color)s%(levelname)s:%(name)s:%(message)s'))

    logging.basicConfig(level=cli_args.loglevel, handlers=[handler])

    for i, farg in enumerate(function_args):
        if farg == "cpu":
            if cli_args.cpu:
                function_args[i] = cpu.get_cpu_from_name(cli_args.cpu)
            elif cli_args.mcu:
                cpu = microcontroller.get_cpu_from_mcu(cli_args.mcu)
                function_args[i] = cpu
        else:
            function_args[i] = getattr(cli_args, farg)
            if isinstance(function_args[i], pathlib.Path):
                function_args[i] = function_args[i].resolve()

    warnings.simplefilter("ignore")
    try:
        asyncio.run(run_eager(function(*function_args)))
    except Exception as e:
        # Swallow any exception
        sys.exit(1)
