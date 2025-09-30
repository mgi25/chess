"""Backend package for the Swiss Chess League Manager."""

from __future__ import annotations


def create_app():
    from .app_factory import create_app as _create_app

    return _create_app()


__all__ = ["create_app"]
