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
  internet host are unreachable (#241). This needs Landlock ABI >= 4; with
  ``--required`` an older kernel fails closed instead of running without it.
- Landlock does not cover UDP, raw or packet sockets, so a small seccomp filter
  (installed unprivileged, under no_new_privs) allows only AF_UNIX, AF_NETLINK
  and plain TCP stream sockets, and refuses TCP Fast Open sends (which connect
  without the connect hook) and io_uring (#237). A DNS packet to 1.1.1.1:53
  therefore fails with EACCES before it is sent.
- From ABI 6 the job is also scoped (LANDLOCK_SCOPE_SIGNAL and
  LANDLOCK_SCOPE_ABSTRACT_UNIX_SOCKET): it cannot signal, or reach an abstract
  UNIX socket of, anything outside its own domain — the worker, the harness,
  other jobs (#237).

Process-tree teardown (#237). With scoping available the launcher does not
exec directly: it enters a signal-scoped outer domain, forks, and stays as a
tiny supervisor while the child enters the full (nested) sandbox and execs the
student command. The student cannot signal the supervisor (outer domain), but
the supervisor may signal the whole nested domain; ``kill(-1, SIGKILL)`` from
there reaches exactly this job's processes — including ones that setsid()'d
out of the process group — and nothing else. The supervisor is a child
subreaper, tears the domain down when the student's main process exits, on
SIGTERM/SIGINT/SIGHUP, and when its parent dies (PR_SET_PDEATHSIG), then exits
with the student's status.

Deliberately no network namespace: that needs unprivileged user namespaces,
which the production host blocks, and a vendored copy of Docker's default
seccomp profile was not worth the maintenance; the filter here only adds
denials on top of Docker's profile.
"""

import argparse
import ctypes
import json
import os
import platform
import signal
import struct
import sys
import time

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

# Scopes (ABI >= 6)
SCOPE_ABSTRACT_UNIX_SOCKET = 1 << 0
SCOPE_SIGNAL = 1 << 1
JOB_SCOPES = SCOPE_ABSTRACT_UNIX_SOCKET | SCOPE_SIGNAL

# Rights that may appear on a rule for a regular file (dir-only rights EINVAL)
FILE_COMPATIBLE = FS_EXECUTE | FS_WRITE_FILE | FS_READ_FILE | FS_TRUNCATE | FS_IOCTL_DEV

RO_RIGHTS = FS_EXECUTE | FS_READ_FILE | FS_READ_DIR

PR_SET_PDEATHSIG = 1
PR_SET_SECCOMP = 22
PR_SET_CHILD_SUBREAPER = 36
PR_SET_NO_NEW_PRIVS = 38
SECCOMP_MODE_FILTER = 2

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


def _create_ruleset(abi: int, handled_fs: int, handled_net: int,
                    scoped: int) -> int:
    if abi >= 6:
        attr = struct.pack("QQQ", handled_fs, handled_net, scoped)
    elif abi >= 4:
        attr = struct.pack("QQ", handled_fs, handled_net)
    else:
        attr = struct.pack("Q", handled_fs)
    buf = ctypes.create_string_buffer(attr, len(attr))
    fd = _libc.syscall(SYS_LANDLOCK_CREATE_RULESET, buf, len(attr), 0)
    if fd < 0:
        raise OSError(ctypes.get_errno(), "landlock_create_ruleset failed")
    return fd


def _restrict_self(ruleset_fd: int) -> None:
    try:
        if _libc.syscall(SYS_LANDLOCK_RESTRICT_SELF, ruleset_fd, 0) != 0:
            raise OSError(ctypes.get_errno(), "landlock_restrict_self failed")
    finally:
        os.close(ruleset_fd)


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
    """Restrict this process to the given paths; deny TCP unless allowed.

    Fails (OSError) rather than silently dropping the network rules when the
    kernel's Landlock cannot express them (ABI < 4). From ABI 6 the domain is
    also scoped: no signals to, or abstract UNIX sockets of, the outside.
    """
    abi = _landlock_abi()
    if abi <= 0:
        raise OSError("Landlock is not available on this kernel")
    if not allow_net and abi < 4:
        raise OSError(f"Landlock ABI {abi} cannot restrict TCP (needs >= 4)")
    fs_mask = _fs_mask(abi)
    handled_net = 0 if allow_net else (NET_BIND_TCP | NET_CONNECT_TCP)
    scoped = JOB_SCOPES if abi >= 6 else 0
    ruleset_fd = _create_ruleset(abi, fs_mask, handled_net, scoped)
    try:
        for path in ro_paths:
            _add_path_rule(ruleset_fd, path, RO_RIGHTS)
        for path in rw_paths:
            _add_path_rule(ruleset_fd, path, fs_mask)
        # No net rules added: with handled_access_net set, all TCP is denied.
        _set_no_new_privs()
    except BaseException:
        os.close(ruleset_fd)
        raise
    _restrict_self(ruleset_fd)


def enter_scope_domain() -> None:
    """Enter a domain that only scopes signals/abstract sockets (ABI >= 6).

    This is the supervisor's outer domain: it can signal the job's nested
    domain but nothing outside, so kill(-1) from it hits only the job.
    """
    abi = _landlock_abi()
    if abi < 6:
        raise OSError(f"Landlock ABI {abi} has no scoping (needs >= 6)")
    _set_no_new_privs()
    _restrict_self(_create_ruleset(abi, 0, 0, JOB_SCOPES))


# --- seccomp socket filter (#237) -------------------------------------------
# Landlock restricts TCP only. This classic-BPF filter closes the rest of the
# network: sockets other than AF_UNIX, AF_NETLINK and TCP stream sockets fail
# with EACCES (no UDP/DNS, raw, packet, SCTP, MPTCP, vsock...), TCP Fast Open
# sends (MSG_FASTOPEN connects without the connect hook) are refused, and
# io_uring (whose socket ops bypass seccomp) reports ENOSYS. Non-native
# syscall ABIs (i386 socketcall, x32) are refused or killed outright.

# arch -> (AUDIT_ARCH, socket, sendto, sendmsg, sendmmsg)
_SECCOMP_ARCH = {
    "x86_64": (0xC000003E, 41, 44, 46, 307),
    "aarch64": (0xC00000B7, 198, 206, 211, 269),
}
_IO_URING_SYSCALLS = (425, 426, 427)  # setup/enter/register, both arches
AF_UNIX, AF_INET, AF_INET6, AF_NETLINK = 1, 2, 10, 16
SOCK_STREAM, SOCK_TYPE_MASK = 1, 0xF
IPPROTO_TCP = 6
MSG_FASTOPEN = 0x20000000
X32_SYSCALL_BIT = 0x40000000
EACCES, ENOSYS = 13, 38

_BPF_LD_ABS, _BPF_JEQ, _BPF_JGE, _BPF_JSET = 0x20, 0x15, 0x35, 0x45
_BPF_AND, _BPF_RET = 0x54, 0x06
_RET_ALLOW, _RET_ERRNO, _RET_KILL = 0x7FFF0000, 0x00050000, 0x80000000


def _arg(i: int) -> int:
    """Offset of the low 32 bits of seccomp_data.args[i] (little-endian)."""
    return 16 + 8 * i


def _seccomp_program():
    machine = platform.machine()
    if machine not in _SECCOMP_ARCH:
        raise OSError(f"no seccomp socket filter for {machine}")
    arch, nr_socket, nr_sendto, nr_sendmsg, nr_sendmmsg = _SECCOMP_ARCH[machine]
    # (code, k, jump-if-true label, jump-if-false label); None = next insn
    code = [
        (_BPF_LD_ABS, 4, None, None),                  # arch
        (_BPF_JEQ, arch, None, "kill"),
        (_BPF_LD_ABS, 0, None, None),                  # syscall nr
        (_BPF_JGE, X32_SYSCALL_BIT, "deny", None),
        (_BPF_JEQ, nr_socket, "socket", None),
        (_BPF_JEQ, nr_sendto, "flags3", None),
        (_BPF_JEQ, nr_sendmmsg, "flags3", None),
        (_BPF_JEQ, nr_sendmsg, "flags2", None),
    ] + [(_BPF_JEQ, nr, "nosys", None) for nr in _IO_URING_SYSCALLS] + [
        (_BPF_RET, _RET_ALLOW, None, None),
        "socket",
        (_BPF_LD_ABS, _arg(0), None, None),            # domain
        (_BPF_JEQ, AF_UNIX, "allow", None),
        (_BPF_JEQ, AF_NETLINK, "allow", None),
        (_BPF_JEQ, AF_INET, "inet", None),
        (_BPF_JEQ, AF_INET6, "inet", "deny"),
        "inet",
        (_BPF_LD_ABS, _arg(1), None, None),            # type | flags
        (_BPF_AND, SOCK_TYPE_MASK, None, None),
        (_BPF_JEQ, SOCK_STREAM, None, "deny"),
        (_BPF_LD_ABS, _arg(2), None, None),            # protocol
        (_BPF_JEQ, 0, "allow", None),
        (_BPF_JEQ, IPPROTO_TCP, "allow", "deny"),
        "flags3",
        (_BPF_LD_ABS, _arg(3), None, None),
        (_BPF_JSET, MSG_FASTOPEN, "deny", "allow"),
        "flags2",
        (_BPF_LD_ABS, _arg(2), None, None),
        (_BPF_JSET, MSG_FASTOPEN, "deny", "allow"),
        "allow",
        (_BPF_RET, _RET_ALLOW, None, None),
        "deny",
        (_BPF_RET, _RET_ERRNO | EACCES, None, None),
        "nosys",
        (_BPF_RET, _RET_ERRNO | ENOSYS, None, None),
        "kill",
        (_BPF_RET, _RET_KILL, None, None),
    ]
    labels, insns = {}, []
    for item in code:
        if isinstance(item, str):
            labels[item] = len(insns)
        else:
            insns.append(item)
    program = []
    for index, (op, k, jt, jf) in enumerate(insns):
        rel = [0 if lab is None else labels[lab] - index - 1 for lab in (jt, jf)]
        program.append((op, rel[0], rel[1], k))
    return program


class _SockFilter(ctypes.Structure):
    _fields_ = [("code", ctypes.c_ushort), ("jt", ctypes.c_ubyte),
                ("jf", ctypes.c_ubyte), ("k", ctypes.c_uint)]


class _SockFprog(ctypes.Structure):
    _fields_ = [("len", ctypes.c_ushort),
                ("filter", ctypes.POINTER(_SockFilter))]


def apply_socket_filter() -> None:
    """Install the socket seccomp filter on this process (needs no_new_privs)."""
    program = _seccomp_program()
    filters = (_SockFilter * len(program))(*[_SockFilter(*i) for i in program])
    fprog = _SockFprog(len(program), filters)
    _set_no_new_privs()
    if _libc.prctl(PR_SET_SECCOMP, SECCOMP_MODE_FILTER, ctypes.byref(fprog),
                   0, 0) != 0:
        raise OSError(ctypes.get_errno(), "prctl(PR_SET_SECCOMP) failed")


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


def _scope_holds() -> bool:
    """True if this (scoped) process can no longer signal its parent.

    kill(-1) reports success even when every target was refused, so it cannot
    be used as a probe; the parent (the harness, outside the domain) can.
    """
    try:
        os.kill(os.getppid(), 0)
    except PermissionError:
        return True
    except ProcessLookupError:
        return False
    return False


def _kill_domain(deadline_seconds: float = 5.0) -> None:
    """SIGKILL every process of the job's nested domain and reap them all.

    Only called from the scoped supervisor, where kill(-1) reaches the nested
    domain and nothing else. As a child subreaper we inherit every orphaned
    job process, so waitpid() drains the whole tree.
    """
    deadline = time.monotonic() + deadline_seconds
    while True:
        try:
            os.kill(-1, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass
        try:
            while os.waitpid(-1, os.WNOHANG)[0]:
                pass
        except ChildProcessError:
            return
        if time.monotonic() > deadline:
            return
        time.sleep(0.01)


_HANDLED_SIGNALS = (signal.SIGTERM, signal.SIGINT, signal.SIGHUP)


def _supervise(child: int, parent: int) -> int:
    """Wait for the student's main process, then tear down the whole job."""
    _libc.prctl(PR_SET_CHILD_SUBREAPER, 1, 0, 0, 0)

    def _on_signal(signum, _frame):
        _kill_domain()
        os._exit(128 + signum)

    for sig in _HANDLED_SIGNALS:
        signal.signal(sig, _on_signal)
    # The harness dying (killed on a worker timeout) must not orphan the job.
    _libc.prctl(PR_SET_PDEATHSIG, signal.SIGTERM, 0, 0, 0)
    signal.pthread_sigmask(signal.SIG_UNBLOCK, _HANDLED_SIGNALS)
    if os.getppid() != parent:  # the parent died before PDEATHSIG was set
        _on_signal(signal.SIGTERM, None)

    status = None
    while status is None:
        try:
            pid, st = os.waitpid(-1, 0)
        except ChildProcessError:
            break
        if pid == child:
            status = st
    _kill_domain()
    code = os.waitstatus_to_exitcode(status) if status is not None else 1
    if code < 0:
        # Died by a signal: die the same way so the caller sees -signum.
        for sig in _HANDLED_SIGNALS:
            signal.signal(sig, signal.SIG_DFL)
        signal.signal(-code, signal.SIG_DFL)
        os.kill(os.getpid(), -code)
        return 128 - code
    return code


def _sandbox_self(ro_paths, rw_paths, allow_net: bool) -> None:
    """Full job sandbox: Landlock paths/TCP/scopes, then the socket filter."""
    apply_landlock(ro_paths, rw_paths, allow_net)
    if not allow_net:
        apply_socket_filter()


def probe() -> dict:
    """Capability report: Landlock ABI (0 if unavailable) and what it enables."""
    abi = _landlock_abi()
    return {"landlock_abi": abi, "tcp_rules": abi >= 4, "scoping": abi >= 6,
            "socket_filter": platform.machine() in _SECCOMP_ARCH}


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

    # With scoping (ABI >= 6) stay behind as the job's supervisor; the
    # sandboxed student command runs in a forked child.
    supervised = False
    if _landlock_abi() >= 6:
        try:
            enter_scope_domain()
            supervised = _scope_holds()
            if not supervised:
                raise OSError("signal scoping has no effect")
        except OSError as exc:
            if args.required:
                print(f"sandbox.launch: cannot scope the job: {exc}",
                      file=sys.stderr)
                return 125
    if supervised:
        signal.pthread_sigmask(signal.SIG_BLOCK, _HANDLED_SIGNALS)
        parent = os.getppid()
        child = os.fork()
        if child:
            return _supervise(child, parent)
        signal.pthread_sigmask(signal.SIG_UNBLOCK, _HANDLED_SIGNALS)

    try:
        _sandbox_self(ro_paths, rw_paths, args.allow_net)
    except OSError as exc:
        if args.required:
            print(f"sandbox.launch: cannot apply sandbox: {exc}",
                  file=sys.stderr)
            return 125
        # Best-effort mode (local lecturer runs): continue unsandboxed.

    os.execvp(cmd[0], cmd)
    return 127  # unreachable


if __name__ == "__main__":
    sys.exit(main())
