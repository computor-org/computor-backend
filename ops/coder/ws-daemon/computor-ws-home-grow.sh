#!/usr/bin/env bash
# Grow one workspace home or scratch image: computor-ws-home-grow <volume> <size>
# Works mounted (online ext4 grow) or not. Shrinking is refused.
set -euo pipefail
name="$1"; size="$2"
[[ "$name" =~ ^coder-(home|scratch)-[0-9a-f-]{36}$ ]] || { echo "bad volume name" >&2; exit 2; }
[[ "$size" =~ ^[1-9][0-9]*[MG]$ ]] || { echo "bad size" >&2; exit 2; }
img="/var/lib/computor-ws/homes/$name.img"
[ -f "$img" ] || { echo "no image $img" >&2; exit 1; }
new=$(numfmt --from=iec "$size"); old=$(stat -c %s "$img")
[ "$new" -gt "$old" ] || { echo "refusing to shrink ($old -> $new bytes)" >&2; exit 1; }
truncate -s "$size" "$img"
mnt="/var/lib/computor-ws/mnt/$name"
if mountpoint -q "$mnt"; then
    loop=$(findmnt -n -o SOURCE "$mnt"); losetup -c "$loop"; resize2fs "$loop"
else
    e2fsck -f -p "$img"; resize2fs "$img"
fi
