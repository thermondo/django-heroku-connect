from django.db import NotSupportedError

__all__ = ('WriteNotSupportedError',)


class WriteNotSupportedError(NotSupportedError):
    """Write actions are not supported on read-only tables."""

    pass
