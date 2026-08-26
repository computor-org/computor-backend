"""Unprivileged sandbox launcher for student code (#240, #241).

Exec-shim: ``python -m sandbox.launch --workdir DIR [--ro P]... [--rw P]...
[--allow-net] [--required] -- CMD ARGS...`` applies kernel sandboxing to
itself and then ``exec``s the real command, so the whole student process tree
inherits the restrictions. Two independent layers:

- **Landlock** (kernel LSM, unprivileged, no mount namespaces needed):
  filesystem allow-list — the runtime paths plus the explicit ``--ro``/``--rw``
  paths are reachable, everything else (the reference/example cache under
  ``/tmp/examples`` included) returns EACCES. From ABI 4 on, TCP bind/connect
  is denied wholesale unless ``--allow-net`` is given. Landlock stacks with
  the container's seccomp/AppArmor confinement and works under Docker's
  default profiles.

- **Network namespace** (``unshare(CLONE_NEWUSER | CLONE_NEWNET)``): the
  student process gets a loopback-only network stack, cutting UDP/ICMP/raw
  sockets too. This needs the testing worker's tailored seccomp profile
  (``ops/docker/seccomp-testing-worker.json``); where the default Docker
  profile still blocks ``unshare`` the launcher silently falls back to the
  Landlock TCP restriction. Note the mount-namespace route (bwrap) is NOT
  available in the workers: docker-default AppArmor carries ``deny mount``,
  which would require host-installed AppArmor profiles to lift.

``--required`` makes a Landlock failure fatal (exit 125) instead of falling
back to unsandboxed execution; the testing worker passes it, local lecturer
runs on macOS or old kernels do not. ``COMPUTOR_SANDBOX_DISABLE=1`` in the
launcher's own environment skips everything (debugging escape hatch).

``--probe`` prints a one-line JSON capability report and exits; the executors
log it once per run so worker logs show which layers are active.

Stdlib only — this module must stay importable with no dependencies.
"""

import argparse
import ctypes
import ctypes.util
import json
import os
import struct
import sys

# Landlock syscall numbers (arch-independent for post-5.x syscalls)
SYS_LANDLOCK_CREATE_RULESET = 444
SYS_LANDLOCK_ADD_RULE = 445
SYS_LANDLOCK_RESTRICT_SELF = 446

LANDLOCK_CREATE_RULESET_VERSION = 1  # flag for the ABI probe

# Rule types
LANDLOCK_RULE_PATH_BENEATH = 1

# Filesystem access rights
FS_EXECUTE = 1 << 0
FS_WRITE_FILE = 1 << 1
FS_READ_FILE = 1 << 2
FS_READ_DIR = 1 << 3
FS_REMOVE_DIR = 1 << 4
FS_REMOVE_FILE = 1 << 5
FS_MAKE_CHAR = 1 << 6
FS_MAKE_DIR = 1 << 7
FS_MAKE_REG = 1 << 8
FS_MAKE_SOCK = 1 << 9
FS_MAKE_FIFO = 1 << 10
FS_MAKE_BLOCK = 1 << 11
FS_MAKE_SYM = 1 << 12
FS_REFER = 1 << 13      # ABI >= 2
FS_TRUNCATE = 1 << 14   # ABI >= 3
FS_IOCTL_DEV = 1 << 15  # ABI >= 5

# Network access rights (ABI >= 4)
NET_BIND_TCP = 1 << 0
NET_CONNECT_TCP = 1 << 1

# Rights that may appear on a rule for a regular file (dir-only rights EINVAL)
FILE_COMPATIBLE = FS_EXECUTE | FS_WRITE_FILE | FS_READ_FILE | FS_TRUNCATE | FS_IOCTL_DEV

RO_RIGHTS = FS_EXECUTE | FS_READ_FILE | FS_READ_DIR

PR_SET_NO_NEW_PRIVS = 38

CLONE_NEWUSER = 0x10000000
CLONE_NEWNET = 0x40000000

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
        # No net rules: with handled_access_net set, all TCP is denied.
        _set_no_new_privs()
        if _libc.syscall(SYS_LANDLOCK_RESTRICT_SELF, ruleset_fd, 0) != 0:
            raise OSError(ctypes.get_errno(), "landlock_restrict_self failed")
    finally:
        os.close(ruleset_fd)


def _bring_loopback_up() -> None:
    import fcntl
    import socket
    SIOCGIFFLAGS = 0x8913
    SIOCSIFFLAGS = 0x8914
    IFF_UP = 0x1
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        ifreq = struct.pack("16sh14s", b"lo", 0, b"")
        flags = struct.unpack("16sh14s",
                              fcntl.ioctl(sock, SIOCGIFFLAGS, ifreq))[1]
        fcntl.ioctl(sock, SIOCSIFFLAGS,
                    struct.pack("16sh14s", b"lo", flags | IFF_UP, b""))


def unshare_network() -> bool:
    """Move into a fresh user+net namespace (loopback only). Best-effort:
    returns False where the container's seccomp profile blocks unshare."""
    uid, gid = os.getuid(), os.getgid()
    if _libc.unshare(CLONE_NEWUSER | CLONE_NEWNET) != 0:
        return False
    try:
        with open("/proc/self/setgroups", "w") as f:
            f.write("deny")
        with open("/proc/self/uid_map", "w") as f:
            f.write(f"{uid} {uid} 1")
        with open("/proc/self/gid_map", "w") as f:
            f.write(f"{gid} {gid} 1")
    except OSError:
        # Namespace exists (network already cut); an unfinished id mapping
        # only leaves the process as the overflow uid, which is harmless here.
        pass
    try:
        _bring_loopback_up()
    except OSError:
        pass
    return True


def _runtime_ro_paths():
    """Fixed read-only runtime paths, plus this interpreter's own prefixes.

    The launcher runs as the framework interpreter and execs the student's;
    for the Python testers they are the same binary, so a virtualenv's prefix
    (which holds pyvenv.cfg and the base stdlib) must be reachable or the child
    cannot even import ``site``.
    """
    return list(DEFAULT_RO) + [sys.prefix, sys.base_prefix]


def _existing(paths):
    seen = []
    for path in paths:
        expanded = os.path.expanduser(path)
        if expanded and os.path.exists(expanded) and expanded not in seen:
            seen.append(expanded)
    return seen


def probe() -> dict:
    """Capability report. Must run in a throwaway process: unshare(2) cannot
    be undone, so a successful netns probe poisons the caller."""
    result = {"landlock_abi": _landlock_abi(), "netns": False}
    if sys.platform == "linux":
        result["netns"] = unshare_network()
    return result


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

    if not args.allow_net:
        unshare_network()

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
