#!/bin/bash
# Back-compat wrapper — the maintenance logic lives in ./computor.sh (see ops/lib/common.sh).
exec "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/computor.sh" maintenance "$@"
