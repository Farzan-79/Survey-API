class AIServiceError(Exception):
    """
    Base exception for all AI service related errors.
    """
    pass


class AIServiceUnavailable(AIServiceError):
    """
    Raised when the AI provider cannot process a request.
    """
    pass