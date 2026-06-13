class ProviderError(Exception):
    """Raised when an upstream AI provider (embedding or completion) fails.

    Surfaced to clients as HTTP 502 so a transient model/key failure is not
    mistaken for an internal server bug.
    """

    def __init__(self, message: str = "The AI provider is currently unavailable") -> None:
        super().__init__(message)
        self.message = message
