"""Custom exceptions for the application"""


class ValidationError(Exception):
    """Raised when validation fails"""
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


class AuthorizationError(Exception):
    """Raised when user is not authorized to perform an action"""
    def __init__(self, message="Unauthorized access"):
        self.message = message
        super().__init__(self.message)


class NotFoundError(Exception):
    """Raised when a resource is not found"""
    def __init__(self, message="Resource not found"):
        self.message = message
        super().__init__(self.message)
