import embedded
import embedded.compiler

class RISCV(embedded.CPU):
    def __init__(self, extensions: tuple[str], bits=32):
        self.extensions = extensions
        self.unique_id = "rv" + str(bits) + "".join(extensions)
        self.bits = bits

    def get_arch_cflags(self, compiler: embedded.compiler.Compiler) -> list[str]:
        joined = "_".join(self.extensions).lower()
        flags = [f"--target=riscv{self.bits}", f"-march=rv{self.bits}{joined}"]
        return flags

class Hazard3(RISCV):
    def __init__(self):
        super().__init__(("I", "M", "A", "C", "Zicsr", "Zba", "Zbb", "Zbc", "Zbs", "Zbkb", "Zcb", "Zcmp"))
        self.unique_id = "hazard3"
