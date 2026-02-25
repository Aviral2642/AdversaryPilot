"""Structured logging configuration for AdversaryPilot."""

import logging
import sys


def get_logger(name: str) -> logging.Logger:
    """Get a namespaced logger for an AdversaryPilot module.

    Args:
        name: Module name (e.g., 'adversarypilot.campaign.manager')

    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)


def configure_logging(
    level: int = logging.INFO,
    fmt: str = "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
) -> None:
    """Configure root AdversaryPilot logging.

    Args:
        level: Logging level (default INFO)
        fmt: Log format string
    """
    logger = logging.getLogger("adversarypilot")
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(logging.Formatter(fmt))
        logger.addHandler(handler)
    logger.setLevel(level)
