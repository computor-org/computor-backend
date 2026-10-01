#!/bin/sh
# Seed only repo-shipped Coder templates. Run with /source:ro and /target:rw.
set -eu

source_root=$1
target_root=$2
owner_uid=$3
owner_gid=$4

if [ -L "$target_root" ] || [ ! -d "$target_root" ]; then
    echo "Template target must be a real directory" >&2
    exit 1
fi

# The worker reads this bind-mount as a non-root user, and the deployer must
# retain write access for subsequent starts even if an old release left UID
# 1000 ownership behind. This directory contains templates, never secrets.
chmod a+rX "$target_root"
chown "$owner_uid:$owner_gid" "$target_root"

for source_dir in "$source_root"/*/; do
    [ -d "$source_dir" ] || continue
    name=${source_dir%/}
    name=${name##*/}
    target_dir=$target_root/$name
    backup_dir=$target_root/.computor-backup-$name

    if [ -L "${source_dir%/}" ] || [ -L "$target_dir" ] || [ -L "$backup_dir" ] \
        || [ -L "$target_dir/.computor-managed" ] \
        || [ -L "$backup_dir/.computor-managed" ]; then
        echo "Refusing symlink in managed template path: $name" >&2
        exit 1
    fi

    # A power loss after moving the old directory aside leaves the backup but
    # no active template. Restore it before attempting the next update.
    if [ -e "$backup_dir" ]; then
        if [ ! -d "$backup_dir" ] || [ ! -f "$backup_dir/.computor-managed" ]; then
            echo "Unexpected template backup: $backup_dir" >&2
            exit 1
        fi
        if [ -e "$target_dir" ]; then
            rm -rf "$backup_dir"
        else
            mv "$backup_dir" "$target_dir"
        fi
    fi

    if [ -e "$target_dir" ] && [ ! -f "$target_dir/.computor-managed" ]; then
        echo "Template $name is unmanaged; left unchanged"
        continue
    fi

    staged_dir=$(mktemp -d "$target_root/.computor-stage-$name.XXXXXX")
    if ! cp -R "$source_dir"/. "$staged_dir"/; then
        rm -rf "$staged_dir"
        exit 1
    fi
    : > "$staged_dir/.computor-managed"
    if ! chmod -R a+rX "$staged_dir" || ! chown -R "$owner_uid:$owner_gid" "$staged_dir"; then
        rm -rf "$staged_dir"
        exit 1
    fi

    if [ -e "$target_dir" ]; then
        mv "$target_dir" "$backup_dir"
        if ! mv "$staged_dir" "$target_dir"; then
            mv "$backup_dir" "$target_dir"
            rm -rf "$staged_dir"
            exit 1
        fi
        rm -rf "$backup_dir"
        echo "Synced managed template: $name"
    else
        mv "$staged_dir" "$target_dir"
        echo "Copied template: $name"
    fi
done
