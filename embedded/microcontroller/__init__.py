import collections.abc
import logging
from embedded import build
from lxml import etree
from cmsis_svd.parser import SVDParser
try:
    import cmsis_pack_manager as cmsis_packs
    from embedded.cpu import arm
    cmsis_cache = None
except ImportError:
    cmsis_packs = None

logger = logging.getLogger(__name__)

KB = 1024
MB = 1024 * 1024

INDENT = "    "

class Microcontroller:
    def __init__(self, part, cpu, pack, svd_filename):
        self.part = part
        self.cpu = cpu
        self.pack = pack
        self.svd = svd_filename
        with self.pack.open(self.svd) as f:
            parser = SVDParser(etree.parse(f))
        self.device = parser.get_device()

    @build.run_in_thread
    def generate_c_header(self, target_peripheral, output_file):
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with output_file.open("w") as output:
            output.write("#pragma once\n\n#include <stdbool.h>\n#include <stdint.h>\n\n")
            instances = []
            for peripheral in self.device.peripherals:
                if target_peripheral != peripheral.group_name and target_peripheral != peripheral.name and target_peripheral != peripheral.derived_from:
                    continue
                instances.append(f"{peripheral.group_name}_Type* {peripheral.name} = ({peripheral.group_name}_Type*) 0x{peripheral.base_address:08x};\n")
                instances.append(f"{peripheral.group_name}_Raw_Type* {peripheral.name}_REGS = ({peripheral.group_name}_Raw_Type*) 0x{peripheral.base_address:08x};\n")
                if peripheral.derived_from is not None:
                    continue
                registers = []
                raw_registers = []
                for r in peripheral.registers:
                    r_description = r.description
                    if "\n" in r_description:
                        r_description = " ".join([x.strip() for x in r_description.split("\n")])
                    fields = list(r.fields)
                    reg_comment = (f"{INDENT}// {r_description}\n{INDENT}//\n",
                                   f"{INDENT}// Address offset: {r.address_offset}\n")
                    registers.extend(reg_comment)
                    raw_registers.extend(reg_comment)
                    if len(fields) == 1 and fields[0].bit_offset == 0 and fields[0].bit_width == r.size:
                        registers.append(f"{INDENT}uint32_t {r.name};\n\n")
                        raw_registers.append(f"{INDENT}uint32_t {r.name};\n\n")
                    else:
                        current_offset = 1
                        output.write(f"// {r_description}\n")
                        output.write(f"typedef struct _{peripheral.group_name}_{r.name}_Type {{\n")
                        fields.sort(key=lambda x: x.bit_offset)
                        for f in fields:
                            description = f.description
                            if "\n" in description:
                                description = " ".join([x.strip() for x in description.split("\n")])
                            if current_offset < f.bit_offset:
                                output.write(f"{INDENT}int reserved_{current_offset}: {f.bit_offset - current_offset};\n")
                                
                            current_offset = f.bit_offset + f.bit_width
                            if f.bit_width == 1:
                                field_type = "bool"
                            elif f.bit_width <= 8:
                                field_type = "uint8_t"
                            else:
                                field_type = "int"
                            output.write(f"{INDENT}{field_type} {f.name}: {f.bit_width}; // {f.bit_offset} {description}\n")
                        output.write(f"}} {peripheral.group_name}_{r.name}_Type;\n\n")
                        registers.append(f"{INDENT}{peripheral.group_name}_{r.name}_Type {r.name};\n\n")
                        raw_registers.append(f"{INDENT}uint32_t {r.name};\n\n")
                output.write(f"typedef struct _{peripheral.group_name}_Type {{\n")
                for r in registers:
                    output.write(r)
                output.write(f"}} {peripheral.group_name}_Type;\n\n")
                output.write(f"typedef struct _{peripheral.group_name}_Raw_Type {{\n")
                for r in raw_registers:
                    output.write(r)
                output.write(f"}} {peripheral.group_name}_Raw_Type;\n\n")
            for i in instances:
                output.write(i)

    @build.run_in_thread
    def generate_linker_script(self, output_file, flash_start_offset=0):
        global cmsis_cache
        if cmsis_cache is None:
            cmsis_cache = cmsis_packs.Cache(True, False)

        device_info = cmsis_cache.index[self.part]
        with output_file.open("w") as output_file:
            output_file.write("MEMORY {\n")
            # Nonvolatile memory (nvm) is where everything stored at start up.
            nvm = None
            # Volatile memory we can write
            ram = None
            for name in device_info["memories"]:
                mem_info = device_info["memories"][name]
                print(name, mem_info)
                start = mem_info["start"] + flash_start_offset
                size = mem_info["size"]
                if size % MB == 0:
                    size = f"{size // MB}M"
                elif size % KB == 0:
                    size = f"{size // KB}K"
                else:
                    size = f"0x{size:x}"
                if mem_info["access"]["execute"] and mem_info["startup"]:
                    nvm = name
                if mem_info["access"]["write"]:
                    ram = name
                attrs = []
                if mem_info["access"]["read"]:
                    attrs.append("r")
                if mem_info["access"]["write"]:
                    attrs.append("w")
                if mem_info["access"]["execute"]:
                    attrs.append("x")
                attrs = "".join(attrs)
                output_file.write(f"{INDENT}{name} ({attrs}) : ORIGIN = 0x{start:08x}, LENGTH = {size}\n")
            output_file.write("}\n")

            output_file.write("ENTRY(Reset_Handler);\n\n")
            output_file.write("SECTIONS {\n")
            output_file.write(f"{INDENT}.text : {{\n")
            output_file.write(f"{INDENT}{INDENT}KEEP(*(.vector_table))\n")
            output_file.write(f"{INDENT}{INDENT}*(.vector_table)\n")
            output_file.write(f"{INDENT}{INDENT}*(.text)\n")
            output_file.write(f"{INDENT}{INDENT}*(.text*)\n")
            output_file.write(f"}} > {nvm}\n")

            output_file.write(f"{INDENT}.rodata : {{\n")
            output_file.write(f"{INDENT}{INDENT}*(.rodata)\n")
            output_file.write(f"{INDENT}{INDENT}*(.rodata*)\n")
            output_file.write(f"}} > {nvm}\n")

            output_file.write(f"{INDENT}.data : {{\n")
            output_file.write(f"{INDENT}{INDENT}*(.data)\n")
            output_file.write(f"{INDENT}{INDENT}*(.data*)\n")
            output_file.write(f"}} > {nvm} AT> {ram} \n")
            output_file.write("_ld_data_start = ADDR(.data);\n")
            output_file.write("_ld_data_nvm_start = LOADADDR(.data);\n")
            output_file.write("_ld_data_size = SIZEOF(.data);\n")

            output_file.write(f"{INDENT}.bss : {{\n")
            output_file.write(f"{INDENT}{INDENT}*(.bss);\n")
            output_file.write(f"{INDENT}{INDENT}*(.bss*);\n")
            output_file.write(f"}} > {ram} \n")
            output_file.write("_ld_bss_start = ADDR(.bss);\n")
            output_file.write("_ld_bss_size = SIZEOF(.bss);\n")

            output_file.write(f"_ld_ram_end = ORIGIN({ram}) + LENGTH({ram});\n")

            output_file.write("}\n")

    @build.run_in_thread
    def generate_startup_source(self, output_file, flash_start_offset=0, first_function="main", interrupts_used={}):
        global cmsis_cache
        if cmsis_cache is None:
            cmsis_cache = cmsis_packs.Cache(True, False)

        device_info = cmsis_cache.index[self.part]
        interrupts = {}
        interrupt_name_to_value = {}
        for p in self.device.peripherals:
            for i in p.interrupts:
                interrupts[i.value] = i.name
                interrupt_name_to_value[i.name] = i.value

        if isinstance(interrupts_used, collections.abc.Sequence):
            d = {}
            for interrupt in interrupts_used:
                if isinstance(interrupt, str):
                    interrupt = interrupt_name_to_value[interrupt]
                d[interrupt] = interrupts[interrupt] + "_Handler"
            interrupts_used = d
        output_file.parent.mkdir(parents=True, exist_ok=True)
        header_filename = output_file.with_suffix(".h")
        with header_filename.open("w") as header_file:
            header_file.write("#pragma once\n\n")
            header_file.write("#include <stdint.h>\n\n")
            header_file.write("// Where data is loaded in volatile memory (aka RAM)\n")
            header_file.write("extern uint32_t _ld_data_start;\n")
            header_file.write("// Where initial data values are stored in nonvolatile memory (aka flash)\n")
            header_file.write("extern uint32_t _ld_data_nvm_start;\n")
            header_file.write("// How large the data section is in bytes\n")
            header_file.write("extern uint32_t _ld_data_size;\n")
            header_file.write("// Where the bss section starts in volatile memory (aka RAM)\n")
            header_file.write("extern uint32_t _ld_bss_start;\n")
            header_file.write("// How large the bss section is in bytes\n")
            header_file.write("extern uint32_t _ld_bss_size;\n")
            header_file.write("extern uint32_t _ld_ram_end;\n")
            header_file.write("void Reset_Handler(void);\n")
            header_file.write("void Default_Handler(void);\n")
            for v in interrupts_used.values():
                header_file.write(f"void {v}(void);\n")
            header_file.write(f"int {first_function}(void);\n")

        with output_file.open("w") as output_file:
            output_file.write(f"#include \"{header_filename}\"\n\n")

            output_file.write("__attribute__((section(\".vector_table\"),used)) void (*const vector_table[])(void) = {\n")
            output_file.write(f"{INDENT}(void (*)(void)) &_ld_ram_end,\n")
            output_file.write(f"{INDENT}Reset_Handler,\n")
            for i in range(2, 16):
                name = self.cpu.interrupts.get(i - 16, "Reserved")
                output_file.write(f"{INDENT}Default_Handler, // {i - 16} {name}\n")
            for i in range(self.cpu.interrupt_count):
                name = interrupts.get(i, f"IRQ{i}")
                handler = interrupts_used.get(i, "Default_Handler")
                output_file.write(f"{INDENT}{handler}, // {i} {name}\n")
            output_file.write("};\n")

            output_file.write("void Default_Handler(void) {\n")
            output_file.write(f"{INDENT}while (1) {{}}\n")
            output_file.write("}\n\n")

            output_file.write("void Reset_Handler(void) {\n")
            output_file.write(f"{INDENT}// Copy data from flash to RAM\n")
            output_file.write(f"{INDENT}uint32_t* src = &_ld_data_nvm_start;\n")
            output_file.write(f"{INDENT}uint32_t* dest = &_ld_data_start;\n")
            output_file.write(f"{INDENT}for (uint32_t i = 0; i < _ld_data_size / 4; i++) {{\n")
            output_file.write(f"{INDENT}{INDENT}*dest++ = *src++;\n")
            output_file.write(f"{INDENT}}}\n")
            output_file.write(f"{INDENT}// Zero out bss\n")
            output_file.write(f"{INDENT}dest = &_ld_bss_start;\n")
            output_file.write(f"{INDENT}for (uint32_t i = 0; i < _ld_bss_size / 4; i++) {{\n")
            output_file.write(f"{INDENT}{INDENT}*dest++ = 0;\n")
            output_file.write(f"{INDENT}}}\n")
            output_file.write(f"{INDENT}// Call {first_function}\n")
            output_file.write(f"{INDENT}{first_function}();\n")
            output_file.write("}\n")

    def __str__(self):
        return f"{self.part} {self.cpu} {self.pack} {self.svd}"

    def __repr__(self):
        return f"Microcontroller({self.part}, {self.cpu}, {self.pack}, {self.svd})"

def get_mcus_from_string(substr) -> list[Microcontroller]:
    global cmsis_cache
    if not cmsis_packs:
        return []

    if cmsis_cache is None:
        cmsis_cache = cmsis_packs.Cache(True, False)

    mcus = []
    for part in cmsis_cache.index.keys():
        if substr in part:
            device_info = cmsis_cache.index[part]
            if "processor" in device_info:
                logger.warning(device_info["processor"])
            if "processors" in device_info:
                for processor in device_info["processors"]:
                    if "svd" in processor:
                        svd = processor["svd"]
                        del processor["svd"]
                    else:
                        svd = None
                    cpu = arm.ARM.from_pdsc(processor)
                    mcus.append(Microcontroller(part, cpu, cmsis_cache.pack_from_cache(device_info), svd))
    return mcus

def get_cpu_from_mcu(substr):
    if not cmsis_packs:
        return None

    cmsis_cache = cmsis_packs.Cache(True, False)
    print(cmsis_cache)

    target_processor = None
    for part in cmsis_cache.index.keys():
        if substr in part:
            print(part)
            device_info = cmsis_cache.index[part]
            print(device_info)
            print(cmsis_cache.pdsc_from_cache(device_info).read())
            print(cmsis_cache.pack_from_cache(device_info).namelist())
            if "processor" in device_info:
                logger.warning(device_info["processor"])
            if "processors" in device_info:
                for processor in device_info["processors"]:
                    if "svd" in processor:
                        del processor["svd"]
                    if target_processor is None:
                        target_processor = processor
                    elif target_processor != processor:
                        logger.error("mismatched processor", target_processor, processor)
    cpu = arm.ARM.from_pdsc(target_processor)
    return cpu