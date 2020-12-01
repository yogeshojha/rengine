# Base image
FROM python:3-alpine

# Labels and Credits
LABEL \
    name="reNgine" \
    author="Yogesh Ojha <yogesh.ojha11@gmail.com>" \
    description="reNgine is a automated pipeline of recon process, useful for information gathering during web application penetration testing."

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN apk update \
    && apk add --virtual build-deps gcc python3-dev musl-dev \
    && apk add postgresql-dev chromium git netcat-openbsd build-base \
    && pip install psycopg2 \
    && apk del build-deps


# Download and install go 1.14
COPY --from=golang:1.14-alpine /usr/local/go/ /usr/local/go/

# Environment vars
ENV DATABASE="postgres"
ENV GOROOT="/usr/local/go"
ENV GOPATH="/root/go"
ENV PATH="${PATH}:${GOROOT}/bin"
ENV PATH="${PATH}:${GOPATH}/bin"

# Download Go packages
RUN go get -u github.com/tomnomnom/assetfinder github.com/hakluke/hakrawler

RUN GO111MODULE=on go get -u -v github.com/projectdiscovery/httpx/cmd/httpx

RUN GO111MODULE=on go get -u -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder \
    github.com/projectdiscovery/nuclei/v2/cmd/nuclei \
    github.com/lc/gau \
    github.com/projectdiscovery/naabu/cmd/naabu

# Copy requirements
COPY ./requirements.txt /tmp/requirements.txt
RUN pip3 install -r /tmp/requirements.txt

COPY ./tools/OneForAll/requirements.txt /tmp/requirements_oneforall.txt
RUN pip3 install -r /tmp/requirements_oneforall.txt

# Make directory for app
RUN mkdir /app
WORKDIR /app

# Copy source code
COPY . /app/

RUN chmod +x /app/tools/get_dirs.sh
RUN chmod +x /app/tools/get_urls.sh
RUN chmod +x /app/tools/takeover.sh

# run entrypoint.sh
ENTRYPOINT ["/app/docker-entrypoint.sh"]
