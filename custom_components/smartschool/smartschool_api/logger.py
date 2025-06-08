import logging


def setup_logger(lowest_level: int = logging.INFO) -> logging.Logger:
    default_format = "[%(asctime)s] [%(levelname)s] %(name)s > %(message)s"
    logging.basicConfig(format=default_format, level=lowest_level)

    formatter = logging.Formatter(default_format)

    logger = logging.getLogger("smartschool")
    for h in logging.root.handlers:
        h.setFormatter(formatter)

    logger.setLevel(lowest_level)

    return logger
