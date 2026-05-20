class GitServerError(Exception):
    pass

class GitServerDisabledError(GitServerError):
    pass

class GitServerConnectionError(GitServerError):
    pass

class GitServerAuthError(GitServerError):
    pass

class GitUserNotFoundError(GitServerError):
    def __init__(self, username: str):
        super().__init__(f"Git user not found: {username}")
        self.username = username

class GitUserAlreadyExistsError(GitServerError):
    def __init__(self, username: str):
        super().__init__(f"Git user already exists: {username}")
        self.username = username
