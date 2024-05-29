FROM --platform=$BUILDPLATFORM python:3.10-alpine

# Labels and Credits
LABEL \
    name="reNgine" \
    author="Yogesh Ojha <yogesh.ojha11@gmail.com>" \
    description="reNgine is a automated pipeline of recon process, useful for information gathering during web application penetration testing."

# Environment Variables
ENV DEBIAN_FRONTEND="noninteractive" \
    DATABASE="postgres"
ENV USERNAME="rengine"

RUN apk add --no-cache bash postgresql-libs curl && \
    apk add --no-cache py3-pip gcc musl-dev python3-dev pango zlib-dev jpeg-dev openjpeg-dev g++ libffi-dev && \
    apk add --no-cache --virtual .build-deps gcc python3-dev musl-dev postgresql-dev && \
    addgroup --gid 1000 -S $USERNAME && \
    adduser -g 1000 -u 1000 -S --shell /bin/bash --ingroup $USERNAME $USERNAME

USER $USERNAME
ENV PATH=/home/$USERNAME/.local/bin:${PATH}

COPY ./web/pyproject.toml /home/$USERNAME/pyproject.toml
WORKDIR /home/$USERNAME
RUN echo 'PATH="$HOME/.local/bin:${PATH}"' >> $HOME/.bashrc && \
    pip install pipx && pipx install poetry && poetry install

EXPOSE 8000
VOLUME /home/$USERNAME/app
WORKDIR /home/$USERNAME/app
COPY ./web/entrypoint.sh /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]