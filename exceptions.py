"""
Domain Exception Hierarchy for Telegram Sports Betting Bot
Provides standardized, typed application errors for external APIs, database operations,
validation checks, and Telegram handler reporting.
"""


class BotError(Exception):
    """Base exception class for all custom application errors."""

    def __init__(self, message: str, details: str = ""):
        super().__init__(message)
        self.message = message
        self.details = details

    def __str__(self) -> str:
        if self.details:
            return f"{self.message} ({self.details})"
        return self.message


class ExternalAPIError(BotError):
    """Base exception for external HTTP API failures."""

    def __init__(self, message: str, provider: str = "", status_code: int = 0, details: str = ""):
        super().__init__(message, details)
        self.provider = provider
        self.status_code = status_code


class LiveScoreAPIError(ExternalAPIError):
    """Raised when LiveScore CDN API requests or parsing fail."""

    def __init__(self, message: str, details: str = ""):
        super().__init__(message, provider="LiveScore", details=details)


class SportyBetAPIError(ExternalAPIError):
    """Raised when SportyBet factsCenter catalog or orders/share API fails."""

    def __init__(self, message: str, status_code: int = 0, details: str = ""):
        super().__init__(message, provider="SportyBet", status_code=status_code, details=details)


class BetCodeConversionError(ExternalAPIError):
    """Raised when RapidAPI ConvertBetCodes or Betloy code conversion fails."""

    def __init__(self, message: str, provider: str = "ConvertBetCodes", details: str = ""):
        super().__init__(message, provider=provider, details=details)


class DatabaseError(BotError):
    """Raised when SQLite database access or query execution fails."""

    def __init__(self, message: str, query: str = "", details: str = ""):
        super().__init__(message, details)
        self.query = query


class ValidationError(BotError):
    """Raised when input parameter or business rule validation fails."""

    def __init__(self, message: str, field_name: str = "", details: str = ""):
        super().__init__(message, details)
        self.field_name = field_name
