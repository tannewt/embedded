try:
    import cmsis_pack_manager as cmsis_packs
    from embedded.cpu import arm
except ImportError:
    cmsis_packs = None

def get_cpu_from_mcu(substr):
    print("get_cpu_from_mcu", substr)
    if not cmsis_packs:
        return None

    print("looking in cmsis packs")
    cmsis_cache = cmsis_packs.Cache(True, False)

    target_processor = None
    for part in cmsis_cache.index.keys():
        if substr in part:
            print(part)
            device_info = cmsis_cache.index[part]
            if "processor" in device_info:
                print(device_info["processor"])
            if "processors" in device_info:
                for processor in device_info["processors"]:
                    if "svd" in processor:
                        del processor["svd"]
                    if target_processor is None:
                        target_processor = processor
                    elif target_processor != processor:
                        print("mismatched processor", target_processor, processor)
    print(target_processor)
    cpu = arm.ARM.from_pdsc(target_processor)
    return cpu