# Base image
FROM ubuntu:20.04

# Labels and Credits
LABEL \
    name="reNgine" \
    author="Yogesh Ojha <yogesh.ojha11@gmail.com>" \
    description="reNgine is a automated pipeline of recon process, useful for information gathering during web application penetration testing."

# Environment Variables
ENV DEBIAN_FRONTEND="noninteractive" \
    DATABASE="postgres"

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install essentials
RUN apt update -y && apt install -y  --no-install-recommends \
    build-essential \
    chromium-browser \
    postgresql \
    libpq-dev \
    gcc \
    libpq-dev \
    netcat \
    wget \
    git \
    libpcap-dev \
    python3-dev \
    python3-pip


# Download and install go 1.14
RUN wget https://dl.google.com/go/go1.14.linux-amd64.tar.gz
RUN tar -xvf go1.14.linux-amd64.tar.gz
RUN mv go /usr/local

# ENV for Go
ENV GOROOT="/usr/local/go"
ENV PATH="${PATH}:${GOROOT}/bin"
ENV PATH="${PATH}:${GOPATH}/bin"

# Download Go packages
RUN go get -u github.com/tomnomnom/assetfinder github.com/hakluke/hakrawler

RUN GO111MODULE=on go get -v github.com/projectdiscovery/httpx/cmd/httpx

RUN GO111MODULE=on go get -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder
RUN GO111MODULE=on go get -v github.com/projectdiscovery/nuclei/v2/cmd/nuclei
RUN GO111MODULE=on go get -v github.com/projectdiscovery/naabu/v2/cmd/naabu
RUN GO111MODULE=on go get -u github.com/tomnomnom/unfurl
RUN GO111MODULE=on go get -u -v github.com/bp0lr/gauplus
RUN GO111MODULE=on go get github.com/tomnomnom/waybackurls
RUN GO111MODULE=on go get -u github.com/jaeles-project/gospider
RUN GO111MODULE=on go get -u github.com/tomnomnom/gf
RUN go get -u github.com/tomnomnom/gf

# Copy requirements
COPY ./requirements.txt /tmp/requirements.txt
RUN pip3 install --upgrade setuptools pip && \
    pip3 install -r /tmp/requirements.txt

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
