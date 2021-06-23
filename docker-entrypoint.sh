#!/bin/bash

if [ "$DATABASE" = "postgres" ]
then
    echo "Waiting for postgres..."

    while ! nc -z db 5432; do
      sleep 0.1
    done

    echo "PostgreSQL started"
fi

python3 manage.py migrate
python3 manage.py collectstatic --no-input --clear

# Load default engine types
python3 manage.py loaddata fixtures/default_scan_engines.yaml --app scanEngine.EngineType
#Load Default keywords
python3 manage.py loaddata fixtures/default_keywords.yaml --app scanEngine.InterestingLookupModel

# update whatportis
# yes | whatportis --update

# install gf patterns
if [ ! -d "~/Gf-Patterns" ];
then
  mkdir ~/.gf
  cp -r $GOPATH/src/github.com/tomnomnom/gf/examples/*.json ~/.gf
  git clone https://github.com/1ndianl33t/Gf-Patterns ~/Gf-Patterns
  mv ~/Gf-Patterns/*.json ~/.gf
fi

# clone eyewitness
if [ ! -d "/app/tools/Eyewitness" ]
then
    git clone https://github.com/FortyNorthSecurity/EyeWitness /app/tools/Eyewitness
fi

# clone theHarvester
if [ ! -d "/app/tools/theHarvester" ]
then
    git clone https://github.com/laramies/theHarvester /app/tools/theHarvester
    python3 -m pip install -r /app/tools/theHarvester/requirements/base.txt
fi

exec "$@"
