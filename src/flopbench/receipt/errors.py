"""Stable, non-secret-bearing receipt errors."""


class ReceiptError(ValueError):
    """A controlled receipt preparation or verification failure."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
