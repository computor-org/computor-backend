Placeholder so `workspace-ingress` always has a certificate directory to mount.

Leaving it empty makes Traefik fall back to its self-signed default certificate,
which is fine in dev (workspaces talk plain HTTP there) and NOT fine in
production: a workspace hitting the public HTTPS URL would reject it.

In production set `WORKSPACE_INGRESS_TLS_DIR` in `.env` to a directory holding
`fullchain.pem` and `privkey.pem` for `PUBLIC_DOMAIN` — the same certificate the
host nginx serves. Traefik's file provider does not reliably reload on a
content-only change, so restart `workspace-ingress` after a renewal.
