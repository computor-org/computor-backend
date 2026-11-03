# Contributing to Computor

This repository holds the whole platform: the Python packages (`computor-types`,
`computor-client`, `computor-backend`), the grading framework (`computor-testing`),
the web frontend (`computor-web`) and the operations tooling (`ops/`).

## Set up

Follow [docs/development.md](docs/development.md) for the backend and web
frontend. For the grading framework see
[computor-testing/docs/DEVELOPER_GUIDE.md](computor-testing/docs/DEVELOPER_GUIDE.md);
for Docker, environment variables and deployment see [ops/README.md](ops/README.md)
and [ops/docs/](ops/docs/).

Install the pre-commit hook once (secret scan, import guard, client-drift check,
web styling ratchet), see [scripts/git-hooks/README.md](scripts/git-hooks/README.md):

```bash
bash scripts/git-hooks/install-hooks.sh
```

## Make a change

1. Branch from `main` (`feat/…`, `fix/…`, `refactor/…`, `docs/…`).
2. After changing DTOs or models, regenerate with `bash generate.sh all`.
3. Run the checks for what you touched:

   ```bash
   ./computor.sh test --unit                      # backend unit tests
   ./computor.sh test --integration               # backend integration tests (dev stack up)

   (cd computor-web && yarn lint && yarn test:public-learning && yarn build)
   (cd computor-web && yarn test:e2e)             # Playwright, backend mocked
   (cd computor-testing && python -m pytest tests) # grading framework
   ```

4. Open a pull request against `main`. Its title becomes the commit subject, so
   write it as a short sentence saying what the change does.

## Merging

Pull requests are merged through the merge queue as one squashed commit. The
required CI check (`ci-gate`) runs in the queue, not on the pull request, so a
pull request shows green before the queue has tested it.

## Licence

By contributing you agree that your code is licensed under the MIT licence
([LICENSE](LICENSE)) and your documentation under CC BY 4.0
([LICENSE-DOCS](LICENSE-DOCS)).
