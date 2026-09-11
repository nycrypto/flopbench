"""Controlled simulator errors."""


class SimulationError(ValueError):
    """A stable, user-safe simulation failure."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
