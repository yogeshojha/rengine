# First run

```
cp .env.example .env
sed -i "s/^SECRET_KEY=.*/SECRET_KEY=$(openssl rand -hex 32)/" .env
make up
make migrate        # then restart the api
```

Every service reads `.env`; compose will not start without it.

# Migrations

Migrations are hand-written under `alembic/versions/`.

```
make migrate-create m="name"   # an empty revision to hand-write
make migrate-draft  m="name"   # autogenerate a draft to edit down
make migrate                   # apply everything pending
make migrate-history           # show the chain
make migrate-downgrade         # roll the last one back
```

Apply migrations before restarting the api.

# Checks

```
make lint    # lint-python, then lint-frontend
make test    # test-python, then test-frontend
```

CI runs the same four targets, so a green `make lint` and `make test` is a
green CI run:

- `make lint-python`: `make check-lists`, then ruff check and ruff format
  over every package in the Makefile's `PACKAGES`, with the ruff version
  `pyproject.toml` pins (run through `uvx`, so the host ruff does not matter).
- `make lint-frontend`: prettier and eslint.
- `make test-python`: pytest in a one-off container of the api service
  (`docker compose run --rm --no-deps api`); db and redis must be up.
- `make test-frontend`: svelte-check and vitest. Run `npm ci` in `frontend/`
  first.

`make check-lists` compares the copies of the package list that tools cannot
share (the pre-commit pattern, compose's `&api-volumes` and `&worker-volumes`,
the Dockerfile `COPY` lines and `RELOAD_DIRS` in `api/entrypoint.sh`) with the
Makefile's `PACKAGES`, and the pre-commit ruff rev with the `pyproject.toml`
pin. A new package goes into all of them.
