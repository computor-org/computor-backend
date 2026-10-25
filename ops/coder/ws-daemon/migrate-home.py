#!/usr/bin/env python3
"""Copy one main-daemon home volume into a workspace-daemon home image.

  migrate-home.py SRC_VOLUME [--target NAME] [--manifests DIR]

SRC_VOLUME is a local volume of the main dockerd (coder-home-<owner>); it is
only read. The target image (default: same name) is created with the size the
computor-home plugin would use, filled with rsync -aHAX --numeric-ids, and every
owner is shifted into the workspace daemon's userns-remap range (uid u ->
base + u). A manifest of the source (path, type, mode, owner, size, mtime,
sha256 or link target, xattr names) is written before the copy and compared
with the target's manifest, with the shift undone, after it; any difference
fails the run and leaves the target image in place for inspection. Run with
the source volume unused (workspace stopped).
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile

PLUGIN_ENV = "/etc/default/computor-ws-homes"


def env():
    values = {"WS_HOMES_IMAGE_DIR": "/var/lib/computor-ws/homes", "WS_HOMES_HOME_SIZE": "5G",
              "WS_HOMES_REMAP_USER": "computor-ws"}
    if os.path.exists(PLUGIN_ENV):
        for line in open(PLUGIN_ENV):
            key, sep, value = line.strip().partition("=")
            if sep and not key.startswith("#"):
                values[key] = value
    return values


def subid_base(path, user):
    for line in open(path):
        name, start, _ = line.strip().split(":")
        if name == user:
            return int(start)
    raise SystemExit(f"{user} not in {path}")


def manifest(root, shift=0):
    entries = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames.sort()
        for name in [""] + sorted(dirnames + filenames) if dirpath == root else sorted(dirnames + filenames):
            path = os.path.join(dirpath, name) if name else dirpath
            st = os.lstat(path)
            rel = os.path.relpath(path, root)
            kind = "l" if os.path.islink(path) else "d" if os.path.isdir(path) else \
                "f" if os.path.isfile(path) else "o"
            if kind == "f":
                h = hashlib.sha256()
                with open(path, "rb") as fh:
                    for chunk in iter(lambda: fh.read(1 << 20), b""):
                        h.update(chunk)
                content = h.hexdigest()
            elif kind == "l":
                content = os.readlink(path)
            else:
                content = ""
            try:
                xattrs = sorted(os.listxattr(path, follow_symlinks=False))
            except OSError:
                xattrs = []
            entries.append([rel, kind, st.st_mode, st.st_uid - shift, st.st_gid - shift,
                            st.st_size if kind != "d" else 0,
                            st.st_mtime_ns if kind != "l" else 0, st.st_nlink if kind == "f" else 0,
                            content, xattrs])
    entries.sort()
    return entries


def run(*cmd):
    subprocess.run(cmd, check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("--target")
    ap.add_argument("--manifests", default="/root/ws-home-migration")
    args = ap.parse_args()
    target = args.target or args.src
    cfg = env()
    src = subprocess.run(["docker", "volume", "inspect", "-f", "{{.Driver}} {{.Mountpoint}}", args.src],
                         check=True, capture_output=True, text=True).stdout.split()
    if src[0] != "local":
        raise SystemExit(f"{args.src}: driver {src[0]}, expected local")
    src_dir = src[1]
    img = os.path.join(cfg["WS_HOMES_IMAGE_DIR"], target + ".img")
    if os.path.exists(img):
        raise SystemExit(f"{img} exists; refusing to overwrite")
    acl = subprocess.run(["getfacl", "-R", "-s", "-p", src_dir], capture_output=True, text=True)
    if acl.stdout.strip():
        raise SystemExit(f"{args.src}: has extended ACLs; migrate by hand")
    base_u = subid_base("/etc/subuid", cfg["WS_HOMES_REMAP_USER"])
    base_g = subid_base("/etc/subgid", cfg["WS_HOMES_REMAP_USER"])
    if base_u != base_g:
        raise SystemExit("subuid and subgid bases differ")
    os.makedirs(args.manifests, mode=0o700, exist_ok=True)
    before = manifest(src_dir)
    if any(not (0 <= e[3] < 65536 and 0 <= e[4] < 65536) for e in before):
        raise SystemExit(f"{args.src}: owner outside 0..65535")
    used = sum(e[5] for e in before)
    size = cfg["WS_HOMES_HOME_SIZE"]
    with open(os.path.join(args.manifests, f"{target}.before.json"), "w") as fh:
        json.dump(before, fh)

    owner = before[0]  # the volume root
    tmp = img + ".new"
    with open(tmp, "wb") as fh:
        os.fchmod(fh.fileno(), 0o600)
    run("truncate", "-s", size, tmp)
    if used > 0.8 * os.path.getsize(tmp):
        os.unlink(tmp)
        raise SystemExit(f"{args.src}: {used} bytes do not fit {size} with headroom; set a size")
    run("mkfs.ext4", "-q", "-F", "-m", "0", "-L", target[-16:],
        "-E", f"root_owner={owner[3] + base_u}:{owner[4] + base_g}", tmp)
    mnt = tempfile.mkdtemp(prefix="ws-home-migrate-")
    run("mount", "-t", "ext4", "-o", "loop,nodev,nosuid", tmp, mnt)
    try:
        run("rsync", "-aHAX", "--numeric-ids", src_dir + "/", mnt + "/")
        for dirpath, dirnames, filenames in os.walk(mnt):
            for name in [""] + dirnames + filenames if dirpath == mnt else dirnames + filenames:
                path = os.path.join(dirpath, name) if name else dirpath
                if name == "lost+found" and dirpath == mnt:
                    continue
                st = os.lstat(path)
                os.lchown(path, st.st_uid + base_u, st.st_gid + base_g)
                if not os.path.islink(path):
                    os.chmod(path, st.st_mode & 0o7777)  # chown clears setuid/setgid
        lf = os.path.join(mnt, "lost+found")
        if os.path.isdir(lf) and not os.path.exists(os.path.join(src_dir, "lost+found")):
            os.rmdir(lf)
        os.utime(mnt, ns=(owner[6], owner[6]))
        after = manifest(mnt, shift=base_u)
    finally:
        run("umount", mnt)
        os.rmdir(mnt)
    with open(os.path.join(args.manifests, f"{target}.after.json"), "w") as fh:
        json.dump(after, fh)
    digest = hashlib.sha256(json.dumps(before).encode()).hexdigest()
    if after != before:
        diff = [e for e in before if e not in after][:3] + [e for e in after if e not in before][:3]
        print(f"MISMATCH {args.src} -> {target}: {diff}", file=sys.stderr)
        raise SystemExit(1)
    os.rename(tmp, img)
    print(f"OK {args.src} -> {target} entries={len(before)} bytes={used} manifest_sha256={digest}")


if __name__ == "__main__":
    main()
