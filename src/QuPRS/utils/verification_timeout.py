"""Typed timeout owned by QuPRS in-process verification.

Do not use a generic TimeoutError for QuPRS deadlines: a hosting
application's SIGALRM or callback may raise TimeoutError independently.
"""


class VerificationTimeout(TimeoutError):
    """QuPRS-owned strategy or in-process verification deadline."""
