"""Git server environment settings.

Only the env-based settings (``config.get_git_server_settings``) survive here:
they configure the single managed git server (Forgejo) whose admin credentials
the *registry* uses to auto-seed its ``GitServer`` row and mint service/clone
tokens. The legacy single-instance ``/git`` admin proxy (get_git_client and the
GitServerClient protocol) was removed — git user/repo lifecycle is handled by
the registry path in ``computor_backend.git_provider``.
"""
