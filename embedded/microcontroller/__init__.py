import logging
try:
    import cmsis_pack_manager as cmsis_packs
    from embedded.cpu import arm
except ImportError:
    cmsis_packs = None

logger = logging.getLogger(__name__)

def get_cpu_from_mcu(substr):
    if not cmsis_packs:
        return None

    cmsis_cache = cmsis_packs.Cache(True, False)

    target_processor = None
    for part in cmsis_cache.index.keys():
        if substr in part:
            device_info = cmsis_cache.index[part]
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