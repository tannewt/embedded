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
    async def compile(self, cpu, source_file: pathlib.Path, output_file: pathlib.Path, flags: list[pathlib.Path], caller_directory : pathlib.Path = None):
        if isinstance(output_file, str):
            output_file = caller_directory / output_file
        if isinstance(source_file, str):
            source_file = caller_directory / source_file
        output_file.parent.mkdir(parents=True, exist_ok=True)
        cpu_flags = cpu.get_arch_cflags(self)
        await build.run_command([self.c_compiler, *cpu_flags, "-MMD", "-c", source_file, *flags, "-o", output_file], description=f"Compile {source_file.relative_to(cwd)} -> {output_file.relative_to(cwd)}", working_directory=caller_directory)
    
    @build.capture_caller_directory
    async def link(self, cpu, objects: list[pathlib.Path], output_file: pathlib.Path, linker_script: pathlib.Path, flags: list[str] = [], print_memory_use=True, output_map_file=True, gc_sections=True, caller_directory=None):
        output_file.parent.mkdir(parents=True, exist_ok=True)
        cpu_flags = cpu.get_arch_cflags(self)
        link_flags = []
        if print_memory_use:
            link_flags.append("-fuse-ld=bfd") # if using clang/LLVM
            link_flags.append("-Wl,--print-memory-usage")
        if output_map_file:
            link_flags.append("-Wl,-Map=" + str(output_file.with_suffix(".elf.map").relative_to(caller_directory)))
        if gc_sections:
            link_flags.append("-Wl,--gc-sections")
        await build.run_command([self.c_compiler, *cpu_flags, *link_flags, *flags, *objects, "-T", linker_script, "-o", output_file], description=f"Link {output_file.relative_to(cwd)}", working_directory=caller_directory)
