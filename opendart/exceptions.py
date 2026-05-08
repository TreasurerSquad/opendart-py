class DartAPIError(Exception):
    """Raised when DART OpenAPI returns a non-success status code."""

    def __init__(self, status: str, message: str):
        self.status = status
        self.message = message
        super().__init__(f"DART API Error [{status}]: {message}")
