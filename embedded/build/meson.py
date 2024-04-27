import embedded
import inspect
from . import run_command
from embedded.cpu import arm, riscv
import pathlib

def create_cross_file(cpu: embedded.CPU, compiler: embedded.Compiler):
    cflags = ",".join(f"'{flag}'" for flag in cpu.get_arch_cflags(compiler))
    link_flags = cflags
    link_flags += ",'-fuse-ld=lld', '-nostdlib'"
    if isinstance(cpu, arm.ARM):
        cpu_family = "arm"
    elif isinstance(cpu, riscv.RISCV):
        cpu_family = f"riscv{cpu.bits}"
    else:
        raise RuntimeError("Unsupported CPU")
    return f"""[binaries]
c = '{compiler.c_compiler}'
cpp = '{compiler.cpp_compiler}'
ar = '{compiler.ar}'
strip = '{compiler.strip}'

[host_machine]
system = ''
kernel = 'none'
cpu_family = '{cpu_family}'
cpu = '{cpu_family}'
endian = 'little'

[built-in options]
c_args = [{cflags}]
c_link_args = [{link_flags}]
"""

async def setup(source_dir, build_dir, cpu: embedded.CPU, compiler: embedded.Compiler, reconfigure=True, options=[]):
    cmd = ["meson", "setup"]
    if reconfigure:
        cmd.append("--reconfigure")

    cross_file = build_dir / "cross_file.txt"
    cross_file.write_text(create_cross_file(cpu, compiler))
    cmd.append("--cross-file")
    cmd.append(str(cross_file))

    for key in options:
        value = options[key]
        if value is False:
            value = "false"
        elif value is True:
            value = "true"
        cmd.append(f"-D{key}={value}")

    cmd.append(source_dir)
    cmd.append(build_dir)

    caller_frame = inspect.stack()[1].filename
    working_directory = pathlib.Path(caller_frame).parent

    await run_command(cmd, working_directory=working_directory)
