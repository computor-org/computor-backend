# Integration tests

Live tests that run against real services (no mocks). Currently:

- `test_course_gitlab_provisioning.py` — the managed-GitLab course provisioning
  (`GitLabProviderClient`): course structure (template/reference/students),
  idempotency, the student fork, and member grants — against a real GitLab.

## Running the GitLab provisioning tests

1. Start a throwaway GitLab (e.g. the one in `../gitlab-local-test`):

   ```bash
   cd ../gitlab-local-test && ./startup.sh      # GitLab CE on http://localhost:8086
   ```

2. Mint an admin token and create a parent group (one-time). With the GitLab
   container running:

   ```bash
   docker exec <gitlab-container> gitlab-rails runner \
     "u=User.find_by_username('root'); \
      u.personal_access_tokens.where(name:'computor-it').delete_all; \
      t=u.personal_access_tokens.create!(scopes:['api','sudo'],name:'computor-it',expires_at:365.days.from_now); \
      puts 'TOKEN='+t.token"

   curl -s -H "PRIVATE-TOKEN: <token>" -X POST http://localhost:8086/api/v4/groups \
     -d "name=computor-it&path=computor-it&visibility=private"   # note the group id
   ```

3. Configure the tests. Either export env vars, or drop them in a **gitignored**
   `integration-tests/.env.gitlab-local`:

   ```
   GITLAB_IT_URL=http://localhost:8086
   GITLAB_IT_TOKEN=<token>
   GITLAB_IT_PARENT_GROUP_ID=<group id>
   ```

4. Run (from the repo root, using the backend venv):

   ```bash
   .venv/bin/python -m pytest integration-tests/test_course_gitlab_provisioning.py -v
   ```

The tests **skip** cleanly if `GITLAB_IT_*` is not configured, so they're safe to
collect without a GitLab. They create real groups/projects/users under the parent
group and tear the course group down afterwards (best-effort).
