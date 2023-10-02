FROM postgres:latest


RUN apt-get update && \
    apt-get install -y git postgresql-server-dev-15 libpam0g-dev libreadline-dev build-essential libselinux1-dev libzstd-dev liblz4-dev zlib1g-dev libkrb5-dev && \
    git clone https://github.com/ossc-db/pg_bulkload && \
    cd pg_bulkload && \
    make USE_PGXS=1 && \
    make USE_PGXS=1 install

# USER postgres
# WORKDIR "/tmp"
# RUN export PATH="/usr/lib/postgresql/15/bin/:$PATH" && \
#     git clone https://github.com/ossc-db/pg_bulkload && \
#     cd pg_bulkload && \
#     make installcheck

ENTRYPOINT ["docker-entrypoint.sh"]

EXPOSE 5432
CMD ["postgres"]

