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
