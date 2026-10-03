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

# Releasing

```
git tag v3.0.1 && git push origin v3.0.1
```

The tag builds the api, worker and frontend images for amd64 and arm64, pushes them to
Docker Hub and `ghcr.io`, then drafts the GitHub release. Publish the draft once the notes read
right. `install.sh` and `rengine update` list a release only after it is published, and by then
its images exist.

A tag with a suffix (`v3.0.1-rc1`) builds the same way, is drafted as a pre-release and leaves
`latest` alone. A push to `master` moves `edge`.

# Checks

```
make lint    # ruff over every package, then prettier and eslint
make test    # pytest in the api container, then svelte-check and vitest
```

Both are what CI runs. `make lint` runs the pinned ruff through `uvx`, which needs uv on the
host. `make lint RUFF=ruff` uses a ruff already on the PATH.
