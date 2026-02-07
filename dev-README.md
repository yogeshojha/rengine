make migrate-create m="name"
make migrate

# Oops, rollback:
make migrate-downgrade

# Check status:
make migrate-history
