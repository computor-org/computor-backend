#!/usr/bin/env python3
"""Docker volume plugin (v1 protocol) that gives every Coder home and scratch
volume of the workspace daemon its own fixed-size ext4 filesystem.

Each volume is a sparse image file under IMAGE_DIR, loop-mounted by this
host-side service (never by a container) under MOUNT_DIR when the workspace
daemon mounts it into a container, and unmounted when the last container
releases it. The filesystem size is the quota: a full home returns ENOSPC to
its own workspace and cannot touch the host or another home. There is no
project quota and no chattr route out of it, and the image file itself is
never visible inside a container.

Driver name: computor-home (the socket name under /run/docker/plugins).
The workspace daemon (dockerd-ws, userns-remap) resolves the unqualified
named volumes in Coder's templates (Binds "coder-home-<owner>:/home/coder",
docker_volume "coder-scratch-<workspace>") to this driver, because Docker
probes every volume driver for an unknown name before creating a local
volume and this driver claims exactly those two name patterns.

Only the workspace daemon may use the driver: calls from any other process
(the main dockerd also probes plugins) are answered with an error. Creation
options are refused, so a caller cannot choose sizes or mount sources; sizes
come from /etc/default/computor-ws-homes and the per-volume override file.
Home volumes cannot be removed through Docker (operator only); scratch
volumes are deleted with their workspace.

Configuration (environment, see computor-ws-homes.default):
  WS_HOMES_IMAGE_DIR, WS_HOMES_MOUNT_DIR, WS_HOMES_HOME_SIZE,
  WS_HOMES_SCRATCH_SIZE, WS_HOMES_SIZES_FILE, WS_HOMES_REMAP_USER,
  WS_HOMES_CONTAINER_UID, WS_HOMES_DAEMON_CONFIG, WS_HOMES_SOCKET.
"""

import json
import os
import re
import socket
import socketserver
import struct
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler

ENV = os.environ.get
IMAGE_DIR = ENV("WS_HOMES_IMAGE_DIR", "/var/lib/computor-ws/homes")
MOUNT_DIR = ENV("WS_HOMES_MOUNT_DIR", "/var/lib/computor-ws/mnt")
HOME_SIZE = ENV("WS_HOMES_HOME_SIZE", "5G")
SCRATCH_SIZE = ENV("WS_HOMES_SCRATCH_SIZE", "5G")
SIZES_FILE = ENV("WS_HOMES_SIZES_FILE", "/etc/computor/ws-home-sizes")
REMAP_USER = ENV("WS_HOMES_REMAP_USER", "computor-ws")
CONTAINER_UID = int(ENV("WS_HOMES_CONTAINER_UID", "1000"))
DAEMON_CONFIG = ENV("WS_HOMES_DAEMON_CONFIG", "/etc/docker/daemon-ws.json")
SOCKET = ENV("WS_HOMES_SOCKET", "/run/docker/plugins/computor-home.sock")
STATE = ENV("WS_HOMES_STATE", "/run/computor-ws-homes/state.json")

NAME_RE = re.compile(r"^coder-(home|scratch)-[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$")
SIZE_RE = re.compile(r"^[1-9][0-9]*[MG]$")
LOCK = threading.Lock()
MOUNTS = {}  # name -> set of mount ids


def log(msg):
    print(msg, file=sys.stderr, flush=True)


def subid_base(path, user):
    with open(path) as fh:
        for line in fh:
            parts = line.strip().split(":")
            if len(parts) == 3 and parts[0] == user:
                return int(parts[1])
    raise RuntimeError(f"{user} has no range in {path}")


def host_owner():
    """Host uid/gid of the container's user under the daemon's userns-remap."""
    return (subid_base("/etc/subuid", REMAP_USER) + CONTAINER_UID,
            subid_base("/etc/subgid", REMAP_USER) + CONTAINER_UID)


def size_for(name):
    try:
        with open(SIZES_FILE) as fh:
            for line in fh:
                key, _, value = line.strip().partition("=")
                if key == name and SIZE_RE.match(value):
                    return value
    except FileNotFoundError:
        pass
    return SCRATCH_SIZE if name.startswith("coder-scratch-") else HOME_SIZE


def image(name):
    return os.path.join(IMAGE_DIR, name + ".img")


def mountpoint(name):
    return os.path.join(MOUNT_DIR, name)


def is_mounted(path):
    with open("/proc/self/mountinfo") as fh:
        return any(line.split()[4] == path for line in fh)


def run(*cmd):
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def create_image(name):
    img = image(name)
    if os.path.exists(img):
        return
    uid, gid = host_owner()
    tmp = img + ".new"
    with open(tmp, "wb") as fh:
        os.fchmod(fh.fileno(), 0o600)
    run("truncate", "-s", size_for(name), tmp)
    run("mkfs.ext4", "-q", "-F", "-m", "0", "-L", name[-16:],
        "-E", f"root_owner={uid}:{gid}", tmp)
    os.rename(tmp, img)
    log(f"created {img} ({size_for(name)})")


def mount(name):
    path = mountpoint(name)
    if is_mounted(path):
        return path
    img = image(name)
    create_image(name)
    # Preen only: replays nothing that the kernel would not, refuses to mount
    # a filesystem with errors that need a human (exit >= 4).
    fsck = subprocess.run(["e2fsck", "-p", img], stdout=subprocess.DEVNULL,
                          stderr=subprocess.PIPE)
    if fsck.returncode >= 4:
        raise RuntimeError(f"e2fsck {img} exit {fsck.returncode}; not mounting")
    os.makedirs(path, mode=0o711, exist_ok=True)
    # Direct I/O on the loop device: otherwise the backing file's page cache
    # is charged to the workspace's memory cgroup on top of the ext4 page
    # cache, and a large write OOM-kills the workspace (seen in rehearsal).
    dev = subprocess.run(["losetup", "--find", "--show", "--direct-io=on", img], check=True,
                         capture_output=True, text=True).stdout.strip()
    try:
        run("mount", "-t", "ext4", "-o", "nodev,nosuid", dev, path)
    except subprocess.CalledProcessError:
        run("losetup", "-d", dev)
        raise
    log(f"mounted {name}")
    return path


def unmount(name):
    path = mountpoint(name)
    if is_mounted(path):
        dev = subprocess.run(["findmnt", "-n", "-o", "SOURCE", path], check=True,
                             capture_output=True, text=True).stdout.strip()
        run("umount", path)
        if dev.startswith("/dev/loop"):
            run("losetup", "-d", dev)
        log(f"unmounted {name}")


def save_state():
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    with open(STATE + ".new", "w") as fh:
        json.dump({k: sorted(v) for k, v in MOUNTS.items()}, fh)
    os.replace(STATE + ".new", STATE)


def load_state():
    try:
        with open(STATE) as fh:
            for name, ids in json.load(fh).items():
                if NAME_RE.match(name) and is_mounted(mountpoint(name)):
                    MOUNTS[name] = set(ids)
    except (FileNotFoundError, ValueError):
        pass


def volume(name):
    path = mountpoint(name)
    return {"Name": name, "Mountpoint": path if is_mounted(path) else "",
            "Status": {"size": size_for(name), "image": os.path.exists(image(name))}}


def handle(op, req):
    if op == "/Plugin.Activate":
        return {"Implements": ["VolumeDriver"]}
    if op == "/VolumeDriver.Capabilities":
        return {"Capabilities": {"Scope": "local"}}
    if op == "/VolumeDriver.List":
        names = sorted({f[:-4] for f in os.listdir(IMAGE_DIR)
                        if f.endswith(".img") and NAME_RE.match(f[:-4])} | set(MOUNTS))
        return {"Volumes": [volume(n) for n in names], "Err": ""}
    name = req.get("Name", "")
    if not NAME_RE.match(name):
        return {"Err": f"computor-home: refusing volume name {name!r}"}
    if op == "/VolumeDriver.Create":
        if req.get("Opts"):
            return {"Err": "computor-home: volume options are not accepted"}
        return {"Err": ""}
    if op == "/VolumeDriver.Get":
        return {"Volume": volume(name), "Err": ""}
    if op == "/VolumeDriver.Path":
        return {"Mountpoint": volume(name)["Mountpoint"], "Err": ""}
    if op == "/VolumeDriver.Mount":
        path = mount(name)
        MOUNTS.setdefault(name, set()).add(req.get("ID", ""))
        save_state()
        return {"Mountpoint": path, "Err": ""}
    if op == "/VolumeDriver.Unmount":
        ids = MOUNTS.get(name, set())
        ids.discard(req.get("ID", ""))
        if not ids:
            MOUNTS.pop(name, None)
            unmount(name)
        save_state()
        return {"Err": ""}
    if op == "/VolumeDriver.Remove":
        if MOUNTS.get(name) or is_mounted(mountpoint(name)):
            return {"Err": f"computor-home: {name} is mounted"}
        if name.startswith("coder-home-"):
            # A user's home outlives workspaces; Docker forgets the volume,
            # the image stays and is found again on next use.
            log(f"remove {name}: kept image (homes are removed by the operator)")
            return {"Err": ""}
        if os.path.exists(image(name)):
            os.unlink(image(name))
            log(f"removed {image(name)}")
        return {"Err": ""}
    return {"Err": f"computor-home: unsupported {op}"}


def peer_is_workspace_daemon(conn):
    """Only the dockerd started with DAEMON_CONFIG may use this driver."""
    try:
        creds = conn.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize("3i"))
        pid, uid, _ = struct.unpack("3i", creds)
        with open(f"/proc/{pid}/cmdline", "rb") as fh:
            args = fh.read().split(b"\0")
        return uid == 0 and DAEMON_CONFIG.encode() in args
    except OSError:
        return False


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_POST(self):
        length = int(self.headers.get("Content-Length") or 0)
        try:
            req = json.loads(self.rfile.read(length) or b"{}")
        except ValueError:
            req = {}
        if self.path != "/Plugin.Activate" and not peer_is_workspace_daemon(self.connection):
            resp = {"Err": "computor-home: serves the workspace daemon only"}
        else:
            try:
                with LOCK:
                    resp = handle(self.path, req)
            except Exception as exc:  # reported to dockerd, which fails the call
                detail = getattr(exc, "stderr", b"") or b""
                log(f"{self.path} {req.get('Name', '')}: {exc} {detail.decode(errors='replace').strip()}")
                resp = {"Err": f"computor-home: {exc}"}
        body = json.dumps(resp).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/vnd.docker.plugins.v1.2+json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class Server(socketserver.ThreadingMixIn, socketserver.UnixStreamServer):
    daemon_threads = True

    def get_request(self):
        conn, _ = self.socket.accept()
        return conn, ("local", 0)


def main():
    os.umask(0o077)
    os.makedirs(IMAGE_DIR, mode=0o700, exist_ok=True)
    # Traverse-only: runc may resolve the bind source as the remapped root.
    os.makedirs(MOUNT_DIR, mode=0o711, exist_ok=True)
    os.chmod(MOUNT_DIR, 0o711)
    host_owner()  # fail at start, not at first mount, if the remap user is missing
    load_state()
    os.makedirs(os.path.dirname(SOCKET), exist_ok=True)
    if os.path.exists(SOCKET):
        os.unlink(SOCKET)
    server = Server(SOCKET, Handler)
    os.chmod(SOCKET, 0o600)
    log(f"computor-home listening on {SOCKET}")
    server.serve_forever()


if __name__ == "__main__":
    main()
