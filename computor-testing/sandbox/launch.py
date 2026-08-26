"""Filesystem+network sandbox for student code, using Landlock (#240, #241).

Landlock is a Linux kernel feature (5.13+): a process can voluntarily drop
itself into an allow-list of file paths it may touch, and — from ABI 4 — a
deny of outbound TCP. It needs no root, no CAP_SYS_ADMIN, and no namespaces,
so it works inside the unprivileged, ``no-new-privileges`` testing worker under
the *default* Docker seccomp profile. Think of it as a per-process firewall for
the filesystem (plus TCP): once applied it cannot be widened, and it is
inherited across ``exec`` and by children.

This module is an exec-shim: ``python launch.py --workdir DIR [--ro P]...
[--rw P]... [--allow-net] [--required] -- CMD ARGS...`` applies Landlock to
itself and then ``exec``s CMD, so the whole student process tree inherits the
restriction. Run it by file PATH (as ctexec does), not ``-m sandbox.launch``:
the child's HOME is redirected into the sandbox dir, so the package would not
be importable — hence this file stays stdlib-only, no imports of its own.

What it guarantees, verified against the running worker:

- The reference/example cache is bound nowhere, so reading it (the master
  solution) returns ``EACCES`` (#240).
- All outbound TCP is denied, so the databases, object store, API and any TCP
  internet host are unreachable (#241). Raw UDP/ICMP egress is NOT covered by
  Landlock; that residual (e.g. a DNS packet) is left to compose-level network
  isolation — see the #237 note in ISSUES-2026.10-BACKLOG.md. Deliberately no
  seccomp profile / network namespace here: that route needs unprivileged user
  namespaces, which this host blocks, and buying it back with a vendored copy
  of Docker's default seccomp profile was not worth the maintenance.

``--required`` makes a Landlock failure fatal (exit 125) instead of running
unsandboxed; the testing worker passes it, local lecturer runs on macOS or old
kernels do not. ``COMPUTOR_SANDBOX_DISABLE=1`` skips everything (debugging).
``--probe`` prints a one-line JSON capability report and exits.
"""

import argparse
import ctypes
import json
import os
import struct
import sys

# Landlock syscall numbers (arch-independent for post-5.x syscalls)
SYS_LANDLOCK_CREATE_RULESET = 444
SYS_LANDLOCK_ADD_RULE = 445
SYS_LANDLOCK_RESTRICT_SELF = 446

LANDLOCK_CREATE_RULESET_VERSION = 1  # flag for the ABI probe

# Rule type
LANDLOCK_RULE_PATH_BENEATH = 1

# Filesystem access rights
FS_EXECUTE = 1 << 0
FS_WRITE_FILE = 1 << 1
FS_READ_FILE = 1 << 2
FS_READ_DIR = 1 << 3
FS_TRUNCATE = 1 << 14   # ABI >= 3
FS_IOCTL_DEV = 1 << 15  # ABI >= 5
FS_REFER = 1 << 13      # ABI >= 2

# Network access rights (ABI >= 4)
NET_BIND_TCP = 1 << 0
NET_CONNECT_TCP = 1 << 1

# Rights that may appear on a rule for a regular file (dir-only rights EINVAL)
FILE_COMPATIBLE = FS_EXECUTE | FS_WRITE_FILE | FS_READ_FILE | FS_TRUNCATE | FS_IOCTL_DEV

RO_RIGHTS = FS_EXECUTE | FS_READ_FILE | FS_READ_DIR

PR_SET_NO_NEW_PRIVS = 38

# Runtime paths every sandboxed process may read/execute (existence-checked).
# ~ is the worker home: language runtimes live there (test venv, R libraries).
# /proc is safe to expose: kernel.yama.ptrace_scope=1 on the target hosts, so
# /proc/<pid>/environ of the worker daemon (which holds API_TOKEN) is not
# readable from a non-descendant even at the same UID.
DEFAULT_RO = ("/usr", "/lib", "/lib64", "/lib32", "/bin", "/sbin", "/etc",
              "/opt", "/proc", "/sys", "~")
# /dev needs writes: /dev/null, /dev/shm (POSIX shared memory), /dev/urandom.
DEFAULT_RW = ("/dev",)

_libc = ctypes.CDLL(None, use_errno=True)


def _landlock_abi() -> int:
    version = _libc.syscall(SYS_LANDLOCK_CREATE_RULESET, None, 0,
                            LANDLOCK_CREATE_RULESET_VERSION)
    return version if version > 0 else 0


def _fs_mask(abi: int) -> int:
    mask = (1 << 13) - 1
    if abi >= 2:
        mask |= FS_REFER
    if abi >= 3:
        mask |= FS_TRUNCATE
    if abi >= 5:
        mask |= FS_IOCTL_DEV
    return mask


def _create_ruleset(abi: int, allow_net: bool) -> int:
    handled_fs = _fs_mask(abi)
    if abi >= 4:
        handled_net = 0 if allow_net else (NET_BIND_TCP | NET_CONNECT_TCP)
        attr = struct.pack("QQ", handled_fs, handled_net)
    else:
        attr = struct.pack("Q", handled_fs)
    buf = ctypes.create_string_buffer(attr, len(attr))
    fd = _libc.syscall(SYS_LANDLOCK_CREATE_RULESET, buf, len(attr), 0)
    if fd < 0:
        raise OSError(ctypes.get_errno(), "landlock_create_ruleset failed")
    return fd


def _add_path_rule(ruleset_fd: int, path: str, rights: int) -> None:
    if not os.path.isdir(path):
        rights &= FILE_COMPATIBLE
    if not rights:
        return
    parent_fd = os.open(path, os.O_PATH | os.O_CLOEXEC)
    try:
        # struct landlock_path_beneath_attr is packed: u64 access, s32 fd
        attr = struct.pack("=Qi", rights, parent_fd)
        buf = ctypes.create_string_buffer(attr, len(attr))
        if _libc.syscall(SYS_LANDLOCK_ADD_RULE, ruleset_fd,
                         LANDLOCK_RULE_PATH_BENEATH, buf, 0) != 0:
            raise OSError(ctypes.get_errno(),
                          f"landlock_add_rule failed for {path}")
    finally:
        os.close(parent_fd)


def _set_no_new_privs() -> None:
    if _libc.prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0) != 0:
        raise OSError(ctypes.get_errno(), "prctl(PR_SET_NO_NEW_PRIVS) failed")


def apply_landlock(ro_paths, rw_paths, allow_net: bool) -> None:
    """Restrict this process to the given paths; deny TCP unless allowed."""
    abi = _landlock_abi()
    if abi <= 0:
        raise OSError("Landlock is not available on this kernel")
    fs_mask = _fs_mask(abi)
    ruleset_fd = _create_ruleset(abi, allow_net)
    try:
        for path in ro_paths:
            _add_path_rule(ruleset_fd, path, RO_RIGHTS)
        for path in rw_paths:
            _add_path_rule(ruleset_fd, path, fs_mask)
        # No net rules added: with handled_access_net set, all TCP is denied.
        _set_no_new_privs()
        if _libc.syscall(SYS_LANDLOCK_RESTRICT_SELF, ruleset_fd, 0) != 0:
            raise OSError(ctypes.get_errno(), "landlock_restrict_self failed")
    finally:
        os.close(ruleset_fd)


def _real_home() -> str:
    """The account's home from the passwd database, not $HOME.

    The child's HOME is redirected into the writable sandbox dir, so relying
    on $HOME here would drop the real home — where the language runtimes and
    per-user virtualenvs live — out of the read-only allow-list.
    """
    try:
        import pwd
        return pwd.getpwuid(os.getuid()).pw_dir
    except (ImportError, KeyError):
        return os.path.expanduser("~")


def _runtime_ro_paths():
    """Fixed read-only runtime paths, plus this interpreter's own prefixes.

    The launcher runs as the framework interpreter and execs the student's;
    for the Python testers they are the same binary, so a virtualenv's prefix
    (which holds pyvenv.cfg and the base stdlib) must be reachable or the child
    cannot even import ``site``.
    """
    return list(DEFAULT_RO) + [sys.prefix, sys.base_prefix]


def _existing(paths):
    home = _real_home()
    seen = []
    for path in paths:
        expanded = home if path == "~" else os.path.expanduser(path)
        if expanded and os.path.exists(expanded) and expanded not in seen:
            seen.append(expanded)
    return seen


def probe() -> dict:
    """Capability report: the Landlock ABI level, 0 if unavailable."""
    return {"landlock_abi": _landlock_abi()}


def main() -> int:
    parser = argparse.ArgumentParser(prog="sandbox.launch",
                                     description=__doc__.splitlines()[0])
    parser.add_argument("--workdir", help="writable working directory")
    parser.add_argument("--ro", action="append", default=[],
                        help="additional read-only path (repeatable)")
    parser.add_argument("--rw", action="append", default=[],
                        help="additional read-write path (repeatable)")
    parser.add_argument("--allow-net", action="store_true",
                        help="do not restrict the network")
    parser.add_argument("--required", action="store_true",
                        help="fail (exit 125) if Landlock cannot be applied")
    parser.add_argument("--probe", action="store_true",
                        help="print a capability report and exit")
    parser.add_argument("cmd", nargs=argparse.REMAINDER,
                        help="-- command to execute")
    args = parser.parse_args()

    if args.probe:
        print(json.dumps(probe()))
        return 0

    cmd = args.cmd
    if cmd and cmd[0] == "--":
        cmd = cmd[1:]
    if not cmd:
        parser.error("no command given after --")

    if os.environ.get("COMPUTOR_SANDBOX_DISABLE") == "1":
        os.execvp(cmd[0], cmd)

    ro_paths = _existing(_runtime_ro_paths() + args.ro)
    rw_paths = _existing(list(DEFAULT_RW) + args.rw
                         + ([args.workdir] if args.workdir else []))
    try:
        apply_landlock(ro_paths, rw_paths, args.allow_net)
    except OSError as exc:
        if args.required:
            print(f"sandbox.launch: cannot apply Landlock sandbox: {exc}",
                  file=sys.stderr)
            return 125
        # Best-effort mode (local lecturer runs): continue unsandboxed.

    os.execvp(cmd[0], cmd)
    return 127  # unreachable


if __name__ == "__main__":
    sys.exit(main())
