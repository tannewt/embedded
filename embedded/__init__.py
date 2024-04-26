"""Python toolkit for building (aka compiling and linking) embedded projects"""

__version__ = "0.0.1"

class Microcontroller:
    pass

class Compiler:
    pass

class CPU:
    def get_arch_cflags(self, compiler: Compiler) -> str:
        return ""
