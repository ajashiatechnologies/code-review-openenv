"""Alternative ASGI entrypoint used by some runtimes."""

from server.app import app

__all__ = ["app"]

