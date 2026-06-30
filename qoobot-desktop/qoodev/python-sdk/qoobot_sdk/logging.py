"""
Logging utilities for QooBot SDK.

Provides structured logging with skill context and timestamped events.
"""

from __future__ import annotations

import logging
import time
from typing import Optional


def get_skill_logger(name: str) -> logging.Logger:
    """Get a logger configured for a specific skill.

    Args:
        name: Skill name

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(f"qoobot.skill.{name}")
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter(
                "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger
