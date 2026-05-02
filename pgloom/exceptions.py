class OrchestratorError(Exception):
    """Base runtime error."""


class NotFoundError(OrchestratorError):
    """Requested row was not found."""


class InvalidTransitionError(OrchestratorError):
    """State transition is not allowed."""


class DuplicateExternalActionError(OrchestratorError):
    """Idempotency key already exists."""
