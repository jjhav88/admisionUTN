"""Configuración centralizada de logging para auditoría y diagnóstico."""

import logging
from logging.config import dictConfig


def setup_logging(debug: bool = False) -> None:
    """Inicializa el logging de la aplicación."""
    level = "DEBUG" if debug else "INFO"
    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
                }
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                }
            },
            "root": {"handlers": ["console"], "level": level},
            "loggers": {
                "admitomi": {"level": level, "propagate": True},
                "uvicorn.access": {"level": "INFO", "propagate": True},
            },
        }
    )


def get_logger(name: str = "admitomi") -> logging.Logger:
    """Obtiene un logger con el nombre indicado."""
    return logging.getLogger(name)
