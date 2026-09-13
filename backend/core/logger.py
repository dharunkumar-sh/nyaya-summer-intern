"""
Structured logging module for the reasoning engine.
"""
import logging
import sys


def setup_logger(name: str = "nyaya_reasoner") -> logging.Logger:
    """Configures structured console logging with timestamp and level."""
    logger = logging.getLogger(name)

    if not logger.handlers:
        logger.setLevel(logging.INFO)
        formatter = logging.Formatter(
            fmt="[%(asctime)s] [%(levelname)s] [%(name)s:%(lineno)d] - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        # Use UTF-8 encoding stream handler or reconfigured stdout to support Tamil & Sanskrit diacritics
        try:
            if hasattr(sys.stdout, "reconfigure"):
                sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            handler = logging.StreamHandler(sys.stdout)
        except Exception:
            handler = logging.StreamHandler(sys.stdout)

        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


logger = setup_logger()
