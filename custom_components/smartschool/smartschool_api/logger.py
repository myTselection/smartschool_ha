import logging


def setup_logger(lowest_level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger("custom_components.smartschool")
    # logger.setLevel(lowest_level)

    return logger
