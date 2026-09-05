import logging
from .config import LOG_FILE, TXT_LOG_FILE


def setup_logging():
    """
    Centralized logging configuration.
    Call ONCE at app startup.
    """

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Prevent duplicate handlers if called multiple times
    if logger.handlers:
        return

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-7s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # ---- Main LOG file (.log) ----
    file_handler_log = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler_log.setFormatter(formatter)

    # ---- TXT copy ----
    file_handler_txt = logging.FileHandler(TXT_LOG_FILE, encoding="utf-8")
    file_handler_txt.setFormatter(formatter)

    # ---- Console ----
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    logger.addHandler(file_handler_log)
    logger.addHandler(file_handler_txt)
    logger.addHandler(stream_handler)