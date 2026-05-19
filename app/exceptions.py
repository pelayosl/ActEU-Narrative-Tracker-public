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


class LabellingLocked(Exception):
    pass
