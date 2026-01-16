"""Structured logging configuration."""
import logging
import sys
import os

import structlog


def setup_logging(log_level: str = None) -> None:
    """
    Configure structured logging for the application.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
    """
    level = log_level or os.getenv("LOG_LEVEL", "INFO")
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=numeric_level,
    )

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            # Use JSON in production, pretty print in development
            structlog.processors.JSONRenderer()
            if os.getenv("ENVIRONMENT") == "production"
            else structlog.dev.ConsoleRenderer(colors=True),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(numeric_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = None) -> structlog.BoundLogger:
    """Get a configured logger instance."""
    return structlog.get_logger(name)
