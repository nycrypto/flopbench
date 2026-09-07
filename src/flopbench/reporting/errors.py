"""Safe public errors that never echo report contents or private paths."""


class ReportError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
