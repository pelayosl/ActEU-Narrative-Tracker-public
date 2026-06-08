class InvalidCredentials(Exception):
    pass


class UserNotFound(Exception):
    pass


class UsernameTaken(Exception):
    def __init__(self, username):
        super().__init__(f"Username '{username}' is already taken")


class TokenExpired(Exception):
    pass


class InvalidToken(Exception):
    pass


class ProjectNotFound(Exception):
    pass


class ProjectAccessDenied(Exception):
    pass


class ClassifierNotFound(Exception):
    pass


class NoPendingPipeline(Exception):
    pass


class PendingPipelineMismatch(Exception):
    """Raised when a pending pipeline exists but its topic_mapping does not
    belong to the classifier targeted for Phase 1 labelling — i.e. the user
    started a new pipeline run before triggering Phase 1 for an earlier classifier."""

    pass


class LabellingLocked(Exception):
    pass
