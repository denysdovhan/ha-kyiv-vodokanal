"""Exceptions of the Kyivvodokanal API."""


class KyivVodokanalError(Exception):
    """Base class for exceptions."""


class KyivVodokanalConnectionError(KyivVodokanalError):
    """Raised for connection errors."""


class KyivVodokanalResponseError(KyivVodokanalError):
    """Raised for unexpected responses."""


class KyivVodokanalAuthError(KyivVodokanalError):
    """Raised when the email or password is rejected."""
