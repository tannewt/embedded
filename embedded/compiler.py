from . import Compiler

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
