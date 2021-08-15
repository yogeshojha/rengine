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
    cmake \
    firefox \
    gcc \
    git \
    libpq-dev \
    libpq-dev \
    libpcap-dev \
    netcat \
    postgresql \
    python3 \
    python3-dev \
    python3-pip \
    python3-netaddr \
    wget \
    x11-utils \
    xvfb

# Download and install go 1.14
RUN wget https://dl.google.com/go/go1.16.5.linux-amd64.tar.gz
RUN tar -xvf go1.16.5.linux-amd64.tar.gz
RUN rm go1.16.5.linux-amd64.tar.gz
RUN mv go /usr/local

# Download geckodriver
RUN wget https://github.com/mozilla/geckodriver/releases/download/v0.26.0/geckodriver-v0.26.0-linux64.tar.gz
RUN tar -xvf geckodriver-v0.26.0-linux64.tar.gz
RUN rm geckodriver-v0.26.0-linux64.tar.gz
RUN mv geckodriver /usr/bin

# ENV for Go
ENV GOROOT="/usr/local/go"
ENV PATH="${PATH}:${GOROOT}/bin"
ENV PATH="${PATH}:${GOPATH}/bin"

ENV GOPATH=$HOME/go
ENV PATH="${PATH}:${GOROOT}/bin:${GOPATH}/bin"

# Make directory for app
WORKDIR /usr/src/app

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

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
RUN go get -v github.com/OWASP/Amass/v3/...
RUN go get -u github.com/tomnomnom/gf

# Copy requirements
COPY ./requirements.txt /tmp/requirements.txt
RUN pip3 install --upgrade setuptools pip && \
    pip3 install -r /tmp/requirements.txt

# install eyewitness

RUN python3 -m pip install fuzzywuzzy \
    selenium \
    python-Levenshtein \
    pyvirtualdisplay \
    netaddr

# Copy source code
COPY . /usr/src/app/

RUN chmod +x /usr/src/app/tools/get_urls.sh
