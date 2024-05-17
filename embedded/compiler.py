import inspect
import pathlib
import asyncio

from . import Compiler
from embedded import build

cwd = pathlib.Path.cwd()

class GCC(Compiler):
    def __init__(self):
        self.c_compiler = "arm-none-eabi-gcc"
        self.cpp_compiler = "arm-none-eabi-g++"
        self.ar = "arm-none-eabi-ar"
        self.strip = "arm-none-eabi-strip"

class Clang(Compiler):
    def __init__(self):
        self.c_compiler = "clang"
        self.cpp_compiler = "clang++"
        self.ar = "llvm-ar"
        self.strip = "llvm-strip"

    @build.capture_caller_directory
    async def preprocess(self, source_file: pathlib.Path, output_file: pathlib.Path, flags: list[pathlib.Path], caller_directory=None):
        output_file.parent.mkdir(parents=True, exist_ok=True)
        await build.run_command([self.c_compiler, "-E", "-MMD", "-c", source_file, *flags, "-o", output_file], description=f"Preprocess {source_file.relative_to(cwd)} -> {output_file.relative_to(cwd)}", working_directory=caller_directory)

    @build.capture_caller_directory
    async def compile(self, cpu, source_file: pathlib.Path, output_file: pathlib.Path, flags: list[pathlib.Path], caller_directory=None):
        output_file.parent.mkdir(parents=True, exist_ok=True)
        cpu_flags = cpu.get_arch_cflags(self)
        await build.run_command([self.c_compiler, *cpu_flags, "-MMD", "-c", source_file, *flags, "-o", output_file], description=f"Compile {source_file.relative_to(cwd)} -> {output_file.relative_to(cwd)}", working_directory=caller_directory)
