#!/bin/sh

cert() {
  COMMON_NAME=${1}
  FILENAME=${2:-app}

  echo "Creating new certificate for ${COMMON_NAME}"
  
  # Generate a new RSA key pair if does not exist
  if ! test -f ${CERT}_rsa.key; then
    openssl genrsa -out ${FILENAME}.key 4096
  else
    mv ${CERT}_rsa.key ${FILENAME}.key
  fi

  # Request a new certificate for the generated key pair
  openssl req -new -sha256 \
     -key ${FILENAME}.key \
     -out ${FILENAME}.csr \
     -subj "/C=${COUNTRY_CODE}/ST=${STATE}/L=${CITY}/O=${COMPANY}/CN=${COMMON_NAME}"

  # Creating SAN extension which is needed by modern browsers
  echo "subjectAltName=DNS:${COMMON_NAME}" > client-ext.cnf

  # Create a new certificate using our own CA
  openssl x509 -req -sha256 -passin pass:${AUTHORITY_PASSWORD} -days 3650 \
    -in ${FILENAME}.csr -CA ca.crt -CAkey ca.key \
    -out ${FILENAME}.crt \
    -extfile client-ext.cnf

  # Rename files and remove useless ones
  mv ${FILENAME}.crt ${FILENAME}.pem
  cp ca.crt ${FILENAME}_chain.pem
  mv ${FILENAME}.key ${FILENAME}_rsa.key
  rm ${FILENAME}.csr
  rm client-ext.cnf
}

# Create /certs folder if it does not exist
[[ -d /certs ]] || mkdir /certs
cd /certs

# Create a new CA if it does not exist
if (! test -f ca.key) || (! test -f ca.crt); then
  echo "Creating new CA..."
  openssl genrsa -out ca.key 4096
  openssl req -new -x509 -sha256 \
   -passin pass:${AUTHORITY_PASSWORD} \
   -passout pass:${AUTHORITY_PASSWORD} \
   -extensions v3_ca -key ca.key -out ca.crt -days 3650 \
   -subj "/C=${COUNTRY_CODE}/O=${COMPANY}/CN=${AUTHORITY_NAME}"

  echo "01" > ca.srl
fi

# Create a new certificate for the DOMAIN_NAME
cert ${DOMAIN_NAME} rengine

# Print all cert files
ls -l /certs

