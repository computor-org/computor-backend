"""
Security utilities for code analysis and protection.

Provides static analysis to detect potentially dangerous code patterns.
"""

import ast
import re
import os
from typing import List, Dict, Any, Set
from dataclasses import dataclass, field

# Import canonical environment definitions from ctexec
from ctexec.environment import DEFAULT_SAFE_ENV, BLOCKED_ENV_VARS


# Modules that should be blocked in student code
BLOCKED_PYTHON_MODULES = {
    # System access
    'os', 'sys', 'subprocess', 'shutil', 'pathlib',

    # Network
    'socket', 'urllib', 'urllib.request', 'urllib.parse',
    'http', 'http.client', 'http.server',
    'requests', 'httpx', 'aiohttp',
    'ftplib', 'smtplib', 'telnetlib', 'poplib', 'imaplib',

    # Process/threading
    'multiprocessing', 'threading', '_thread', 'concurrent',
    'signal', 'pty', 'fcntl', 'termios',

    # Low-level/dangerous
    'ctypes', 'cffi', 'resource',
    'code', 'codeop', 'compile',
    'importlib', 'pkgutil', 'modulefinder',
    '__builtin__', 'builtins',

    # Introspection (can be used to bypass restrictions)
    'gc', 'inspect', 'dis',
}

# Dangerous built-in functions
DANGEROUS_BUILTINS = {
    'eval', 'exec', 'compile', '__import__',
    'open',  # May want to allow in some contexts
    'input',  # May cause hangs
}

# Dangerous patterns in C code
DANGEROUS_C_PATTERNS = [
    r'\bsystem\s*\(',
    r'\bexec[vl]?[pe]?\s*\(',
    r'\bpopen\s*\(',
    r'\bfork\s*\(',
    r'\bgetenv\s*\(',
    r'\bputenv\s*\(',
    r'\bsetenv\s*\(',
    r'\bsocket\s*\(',
    r'\bconnect\s*\(',
    r'\bbind\s*\(',
    r'\blisten\s*\(',
    r'\baccept\s*\(',
]

# Dangerous patterns in Octave/MATLAB code
DANGEROUS_OCTAVE_PATTERNS = [
    r'\bsystem\s*\(',
    r'\bunix\s*\(',
    r'\bdos\s*\(',
    r'\beval\s*\(',
    r'\bfeval\s*\(',
    r'\burlread\s*\(',
    r'\burlwrite\s*\(',
    r'\bwebread\s*\(',
    r'\bwebwrite\s*\(',
]


@dataclass
class SecurityIssue:
    """Represents a detected security issue in code."""
    severity: str  # 'critical', 'high', 'medium', 'low'
    category: str  # 'import', 'builtin', 'pattern', etc.
    message: str
    line_number: int = 0
    code_snippet: str = ""


@dataclass
class SecurityReport:
    """Security analysis report."""
    safe: bool
    issues: List[SecurityIssue] = field(default_factory=list)
    blocked_imports: List[str] = field(default_factory=list)
    dangerous_calls: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary."""
        return {
            'safe': self.safe,
            'issues': [
                {
                    'severity': i.severity,
                    'category': i.category,
                    'message': i.message,
                    'line': i.line_number,
                    'snippet': i.code_snippet,
                }
                for i in self.issues
            ],
            'blocked_imports': self.blocked_imports,
            'dangerous_calls': self.dangerous_calls,
        }


def check_dangerous_imports(code: str,
                             blocked: Set[str] = None) -> List[SecurityIssue]:
    """
    Check Python code for dangerous imports.

    Args:
        code: Python source code
        blocked: Set of blocked module names (default: BLOCKED_PYTHON_MODULES)

    Returns:
        List of SecurityIssue objects
    """
    blocked = blocked or BLOCKED_PYTHON_MODULES
    issues = []

    try:
        tree = ast.parse(code)
    except SyntaxError:
        return issues

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                module = alias.name.split('.')[0]
                if module in blocked:
                    issues.append(SecurityIssue(
                        severity='critical',
                        category='import',
                        message=f"Blocked import: {alias.name}",
                        line_number=node.lineno,
                    ))

        elif isinstance(node, ast.ImportFrom):
            if node.module:
                module = node.module.split('.')[0]
                if module in blocked:
                    issues.append(SecurityIssue(
                        severity='critical',
                        category='import',
                        message=f"Blocked import from: {node.module}",
                        line_number=node.lineno,
                    ))

        # Check for __import__ calls
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id == '__import__':
                issues.append(SecurityIssue(
                    severity='critical',
                    category='builtin',
                    message="Blocked: __import__() call",
                    line_number=node.lineno,
                ))

    return issues


def check_dangerous_builtins(code: str,
                              blocked: Set[str] = None) -> List[SecurityIssue]:
    """
    Check Python code for dangerous built-in function calls.

    Args:
        code: Python source code
        blocked: Set of blocked function names

    Returns:
        List of SecurityIssue objects
    """
    blocked = blocked or DANGEROUS_BUILTINS
    issues = []

    try:
        tree = ast.parse(code)
    except SyntaxError:
        return issues

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func_name = None

            if isinstance(node.func, ast.Name):
                func_name = node.func.id
            elif isinstance(node.func, ast.Attribute):
                func_name = node.func.attr

            if func_name and func_name in blocked:
                issues.append(SecurityIssue(
                    severity='high',
                    category='builtin',
                    message=f"Dangerous function call: {func_name}()",
                    line_number=node.lineno,
                ))

    return issues


def analyze_python_security(code: str) -> SecurityReport:
    """
    Perform full security analysis on Python code.

    Args:
        code: Python source code

    Returns:
        SecurityReport with analysis results
    """
    issues = []

    # Check imports
    import_issues = check_dangerous_imports(code)
    issues.extend(import_issues)

    # Check builtins
    builtin_issues = check_dangerous_builtins(code)
    issues.extend(builtin_issues)

    blocked_imports = [i.message for i in issues if i.category == 'import']
    dangerous_calls = [i.message for i in issues if i.category == 'builtin']

    return SecurityReport(
        safe=len(issues) == 0,
        issues=issues,
        blocked_imports=blocked_imports,
        dangerous_calls=dangerous_calls,
    )


def analyze_c_security(code: str) -> SecurityReport:
    """
    Perform security analysis on C/C++ code.

    Args:
        code: C/C++ source code

    Returns:
        SecurityReport with analysis results
    """
    issues = []

    # Remove comments first
    code_no_comments = re.sub(r'//.*$', '', code, flags=re.MULTILINE)
    code_no_comments = re.sub(r'/\*.*?\*/', '', code_no_comments, flags=re.DOTALL)

    for pattern in DANGEROUS_C_PATTERNS:
        for match in re.finditer(pattern, code_no_comments):
            # Find line number
            line_num = code_no_comments[:match.start()].count('\n') + 1
            issues.append(SecurityIssue(
                severity='high',
                category='pattern',
                message=f"Dangerous function: {match.group(0).strip()}",
                line_number=line_num,
            ))

    return SecurityReport(
        safe=len(issues) == 0,
        issues=issues,
    )


def analyze_octave_security(code: str) -> SecurityReport:
    """
    Perform security analysis on Octave/MATLAB code.

    Args:
        code: Octave/MATLAB source code

    Returns:
        SecurityReport with analysis results
    """
    issues = []

    # Remove comments
    code_no_comments = re.sub(r'[%#].*$', '', code, flags=re.MULTILINE)
    code_no_comments = re.sub(r'%\{.*?%\}', '', code_no_comments, flags=re.DOTALL)

    for pattern in DANGEROUS_OCTAVE_PATTERNS:
        for match in re.finditer(pattern, code_no_comments):
            line_num = code_no_comments[:match.start()].count('\n') + 1
            issues.append(SecurityIssue(
                severity='high',
                category='pattern',
                message=f"Dangerous function: {match.group(0).strip()}",
                line_number=line_num,
            ))

    return SecurityReport(
        safe=len(issues) == 0,
        issues=issues,
    )


class SafeEnvironment:
    """
    Context manager for creating a safe execution environment.

    Provides a clean set of environment variables with no secrets.
    """

    # Use canonical safe environment from ctexec
    SAFE_DEFAULTS = DEFAULT_SAFE_ENV

    # Patterns that indicate sensitive data
    SENSITIVE_PATTERNS = [
        'SECRET', 'PASSWORD', 'TOKEN', 'KEY', 'CREDENTIAL',
        'AUTH', 'API', 'PRIVATE', 'ACCESS',
    ]

    def __init__(self, whitelist: List[str] = None,
                 extra: Dict[str, str] = None):
        """
        Initialize safe environment.

        Args:
            whitelist: Environment variable names to pass through
            extra: Additional environment variables to set
        """
        self.whitelist = whitelist or []
        self.extra = extra or {}
        self._original_env = None

    def get_env(self) -> Dict[str, str]:
        """
        Get the safe environment dictionary.

        Returns:
            Dictionary of safe environment variables
        """
        env = self.SAFE_DEFAULTS.copy()

        # Add whitelisted variables
        for key in self.whitelist:
            if key in os.environ and not self._is_sensitive(key):
                env[key] = os.environ[key]

        # Add extra variables
        for key, value in self.extra.items():
            if not self._is_sensitive(key):
                env[key] = value

        return env

    def _is_sensitive(self, key: str) -> bool:
        """Check if an environment variable name looks sensitive."""
        key_upper = key.upper()
        # Check against canonical blocked list and sensitive patterns
        return (key_upper in BLOCKED_ENV_VARS or
                any(pattern in key_upper for pattern in self.SENSITIVE_PATTERNS))

    def __enter__(self):
        """Set up safe environment."""
        self._original_env = os.environ.copy()
        os.environ.clear()
        os.environ.update(self.get_env())
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Restore original environment."""
        if self._original_env is not None:
            os.environ.clear()
            os.environ.update(self._original_env)
