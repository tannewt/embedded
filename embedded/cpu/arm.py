import embedded
import embedded.compiler

from typing import Optional

class ARM(embedded.CPU):
    def __init__(self, mcpu: str, floating_point: bool = False, floating_point_unit: str = None):
        self.mcpu = mcpu
        self.floating_point = floating_point
        self.floating_point_unit = floating_point_unit
        self.unique_id = mcpu + ("f" if floating_point else "")

    def get_arch_cflags(self, compiler: embedded.Compiler) -> list[str]:
        flags = ["-mthumb"]
        floating_point_unit = self.floating_point_unit
        assert(compiler is not None)
        if isinstance(compiler, embedded.compiler.Clang):
            flags.append("--target=arm-none-eabi")
            flags.append(f"-mcpu={self.mcpu}")
            flags.append(f"-mfpu={floating_point_unit}")
        else:
            flags.append(f"-mcpu={self.mcpu}")
            if self.floating_point_unit is None:
                floating_point_unit = "auto"
            if self.floating_point:
                flags.append(f"-mfpu={self.floating_point_unit}")
        if self.floating_point:
            flags.extend(("-mfloat-abi=hard",))
        return flags

    @staticmethod
    def from_pdsc(description: dict) -> Optional[embedded.CPU]:
        if "core" in description:
            core = description["core"]
            if core == "CortexM0Plus":
                return CortexM0Plus()
            elif core == "CortexM4":
                return CortexM4(description["fpu"])
            elif core == "CortexM7":
                return CortexM7(description["fpu"])
            elif core == "CortexM33":
                return CortexM33(description["fpu"])
        return None

class CortexM0Plus(ARM):
    def __init__(self, small_multiply=False):
        if small_multiply:
            small_multiply = ".small-multiply"
        else:
            small_multiply = ""
        super().__init__("cortex-m0plus" + small_multiply, False)

class CortexM4(ARM):
    def __init__(self, floating_point: bool):
        if floating_point:
            fp = ""
        else:
            fp = "+nofp"
        super().__init__("cortex-m4" + fp, floating_point=floating_point, floating_point_unit="fpv4-sp-d16")

class CortexM7(ARM):
    def __init__(self, floating_point: str):
        if floating_point:
            fp = ""
        else:
            fp = "+nofp"
        super().__init__("cortex-m7" + fp, floating_point)

class CortexM33(ARM):
    def __init__(self, floating_point: str, dsp: bool):
        if floating_point:
            fp = ""
        else:
            fp = "+nofp"
        if dsp:
            dsp_flag = ""
        else:
            dsp_flag = "+nodsp"
        super().__init__("cortex-m33" + fp + dsp_flag, floating_point)
