#!/bin/sh

if [ "$DATABASE" = "postgres" ]
then
    echo "Waiting for postgres..."

    while ! nc -z db 5432; do
      sleep 0.1
    done

    echo "PostgreSQL started"
fi

python manage.py migrate
python manage.py collectstatic --no-input --clear

# Load default engine types
python manage.py loaddata fixtures/default_scan_engines.yaml --app scanEngine.EngineType
#Load Default keywords
python manage.py loaddata fixtures/default_keywords.yaml --app scanEngine.InterestingLookupModel

# update whatportis
yes | whatportis --update

# install gf patterns
if [ ! -d "~/Gf-Patterns" ];
then
  mkdir ~/.gf
  cp -r $GOPATH/src/github.com/tomnomnom/gf/examples ~/.gf
  git clone https://github.com/1ndianl33t/Gf-Patterns ~/Gf-Patterns
  mv ~/Gf-Patterns/*.json ~/.gf
fi

exec "$@"
