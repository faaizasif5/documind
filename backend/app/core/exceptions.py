class ProviderError(Exception):
    """Raised when an upstream AI provider (embedding or completion) fails.

    Surfaced to clients as HTTP 502 so a transient model/key failure is not
    mistaken for an internal server bug.
    """

    def __init__(self, message: str = "The AI provider is currently unavailable") -> None:
        super().__init__(message)
        self.message = message


class ProviderRateLimitError(ProviderError):
    """The provider kept returning 429 after retries, or a daily quota is exhausted.

    ``retry_after_seconds`` is the provider's own retry hint when it gave one, so
    background work can be rescheduled instead of failed.
    """

    def __init__(
        self,
        message: str = "The AI provider rate limit was exceeded",
        *,
        retry_after_seconds: float | None = None,
        daily_quota: bool = False,
    ) -> None:
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds
        self.daily_quota = daily_quota
