"""
Unified exception hierarchy for all executors.

All language-specific executors should use these exceptions
for consistent error handling across the framework.
"""


class ExecutorError(Exception):
    """Base exception for all executor errors."""

    def __init__(
        self,
        message: str,
        stdout: str = "",
        stderr: str = "",
        return_code: int = -1,
        timed_out: bool = False,
    ):
        super().__init__(message)
        self.message = message
        self.stdout = stdout
        self.stderr = stderr
        self.return_code = return_code
        self.timed_out = timed_out

    def __str__(self) -> str:
        parts = [self.message]
        if self.stderr:
            parts.append(f"stderr: {self.stderr[:200]}")
        if self.timed_out:
            parts.append("(timed out)")
        return " | ".join(parts)


class ExecutionError(ExecutorError):
    """Exception raised when code execution fails."""
    pass


class CompilationError(ExecutorError):
    """Exception raised when compilation fails (compiled languages only)."""

    def __init__(
        self,
        message: str,
        stdout: str = "",
        stderr: str = "",
        return_code: int = -1,
        warnings: list = None,
        errors: list = None,
    ):
        super().__init__(message, stdout, stderr, return_code)
        self.warnings = warnings or []
        self.errors = errors or []


class RuntimeNotFoundError(ExecutorError):
    """Exception raised when required runtime/compiler is not installed."""

    def __init__(self, language: str, binary: str = None):
        message = f"{language} runtime not found"
        if binary:
            message += f" (tried: {binary})"
        super().__init__(message)
        self.language = language
        self.binary = binary


class ExecutionTimeoutError(ExecutorError):
    """Exception raised when execution times out."""

    def __init__(
        self,
        message: str,
        stdout: str = "",
        stderr: str = "",
        timeout: float = None,
    ):
        super().__init__(message, stdout, stderr, timed_out=True)
        self.timeout = timeout


# Backward-compatible alias (shadows built-in TimeoutError, deprecated)
TimeoutError = ExecutionTimeoutError
