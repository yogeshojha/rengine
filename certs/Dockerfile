FROM alpine:latest

RUN apk update && \
    apk add --no-cache openssl && \
    rm -rf /var/cache/apk/*

RUN echo "[ v3_ca ]" >>/etc/ssl/openssl.cnf && \
    echo "basicConstraints = critical, CA:TRUE" >>/etc/ssl/openssl.cnf && \
    echo "subjectKeyIdentifier = hash" >>/etc/ssl/openssl.cnf && \
    echo "authorityKeyIdentifier = keyid:always,issuer:always" >>/etc/ssl/openssl.cnf && \
    echo "keyUsage = critical, digitalSignature, cRLSign, keyCertSign" >>/etc/ssl/openssl.cnf

COPY entrypoint.sh /
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
