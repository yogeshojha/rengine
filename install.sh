#!/bin/bash

# Ask the user for the domain name
echo "What's your domain ? ex: rengine.domain.tld"
read domain

echo "What's your email ? ex: contact@domain.tld"
read email

sed -i 's/domain.tld/'$domain'/' ./docker-compose.yml
sed -i 's/contact@domain.tld/'$email'/' ./Traefik/config/traefik.yml

chmod 600 ./Traefik/config/acme.json

cd ./Traefik && docker-compose build && docker-compose up -d