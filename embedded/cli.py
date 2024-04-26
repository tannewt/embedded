import argparse
import inspect

import embedded
from embedded import cpu
from embedded import microcontroller

def run(function):
    function_args = []
    parser = argparse.ArgumentParser()
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

        # print(param, type(param), param.annotation)

    cli_args = parser.parse_args()

    for i, farg in enumerate(function_args):
        if farg == "cpu":
            print(cli_args)
            if cli_args.cpu:
                function_args[i] = cpu.get_cpu_from_name(cli_args.cpu)
            elif cli_args.mcu:
                cpu = microcontroller.get_cpu_from_mcu(cli_args.mcu)
                function_args[i] = cpu

    function(*function_args)