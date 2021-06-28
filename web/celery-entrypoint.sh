#!/bin/bash

if [ "$DATABASE" = "postgres" ]
then
    echo "Waiting for postgres..."

    while ! nc -z db 5432; do
      sleep 0.1
    done

    echo "PostgreSQL started"
fi

python3 manage.py makemigrations
python3 manage.py migrate
python3 manage.py collectstatic --no-input --clear

python3 manage.py loaddata fixtures/default_scan_engines.yaml --app scanEngine.EngineType
#Load Default keywords
python3 manage.py loaddata fixtures/default_keywords.yaml --app scanEngine.InterestingLookupModel

# # update whatportis
# yes | whatportis --update
#
# # clone dirsearch
# if [ ! -d "/usr/src/github/dirsearch" ]
# then
#   echo "Cloning dirsearch"
#   git clone https://github.com/maurosoria/dirsearch /usr/src/github/dirsearch
# fi
#
# python3 -m pip install -r /usr/src/github/dirsearch/requirements.txt
#
# # clone Sublist3r
# if [ ! -d "/usr/src/github/Sublist3r" ]
# then
#   echo "Cloning Sublist3r"
#   git clone https://github.com/aboul3la/Sublist3r /usr/src/github/Sublist3r
# fi
#
# python3 -m pip install -r /usr/src/github/Sublist3r/requirements.txt
#
# # clone OneForAll
# if [ ! -d "/usr/src/github/OneForAll" ]
# then
#   echo "Cloning OneForAll"
#   git clone https://github.com/shmilylty/OneForAll /usr/src/github/OneForAll
# fi
#
# python3 -m pip install -r /usr/src/github/OneForAll/requirements.txt
#
# # clone eyewitness
# if [ ! -d "/usr/src/github/Eyewitness" ]
# then
#   echo "Cloning Eyewitness"
#   git clone https://github.com/FortyNorthSecurity/EyeWitness /usr/src/github/Eyewitness
#   # pip install -r /usr/src/github/Eyewitness/requirements.txt
# fi
#
# # clone theHarvester
# if [ ! -d "/usr/src/github/theHarvester" ]
# then
#   echo "Cloning theHarvester"
#   git clone https://github.com/laramies/theHarvester /usr/src/github/theHarvester
# fi
#
# python3 -m pip install -r /usr/src/github/theHarvester/requirements/base.txt
#
# # install gf patterns
# if [ ! -d "/root/Gf-Patterns" ];
# then
#   echo "Installing GF Patterns"
#   mkdir ~/.gf
#   cp -r $GOPATH/src/github.com/tomnomnom/gf/examples/*.json ~/.gf
#   git clone https://github.com/1ndianl33t/Gf-Patterns ~/Gf-Patterns
#   mv ~/Gf-Patterns/*.json ~/.gf
# fi
#
# # store scan_results
# if [ ! -d "/usr/src/scan_results" ]
# then
#     mkdir /usr/src/scan_results
# fi

exec "$@"
