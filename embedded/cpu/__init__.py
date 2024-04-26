from . import arm
from . import riscv

def get_cpu_from_name(name):
    name = name.lower()
    if name == "hazard3":
        return riscv.Hazard3()
    elif name == "riscv32imac":
        return riscv.RISCV(("I", "M", "A", "C"))
    elif name in ("cm0+", "cortex-m0plus", "cortex-m0+"):
        return arm.CortexM0Plus()
    elif name in ("cm4", "cortex-m4"):
        return arm.CortexM4(False)
    elif name in ("cm4f", "cortex-m4f"):
        return arm.CortexM4(True)
    elif name in ("cm7", "cortex-m7"):
        return arm.CortexM7(False)
