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

# Download and install go 1.17
RUN wget https://golang.org/dl/go1.17.2.linux-amd64.tar.gz
RUN tar -xvf go1.17.2.linux-amd64.tar.gz
RUN rm go1.17.2.linux-amd64.tar.gz
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
RUN go install -v github.com/tomnomnom/assetfinder@latest
RUN go install -v github.com/hakluke/hakrawler@latest

RUN GO111MODULE=on go install -v github.com/projectdiscovery/httpx/cmd/httpx@latest

RUN GO111MODULE=on go install -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest
RUN GO111MODULE=on go install -v github.com/projectdiscovery/nuclei/v2/cmd/nuclei@latest
RUN GO111MODULE=on go install -v github.com/projectdiscovery/naabu/v2/cmd/naabu@latest
RUN GO111MODULE=on go install -v github.com/tomnomnom/unfurl@latest
RUN GO111MODULE=on go install -v -v github.com/bp0lr/gauplus@latest
RUN GO111MODULE=on go install -v github.com/tomnomnom/waybackurls@latest
RUN GO111MODULE=on go install -v github.com/jaeles-project/gospider@latest
RUN GO111MODULE=on go install -v github.com/tomnomnom/gf@latest
RUN go install -v github.com/OWASP/Amass/v3/...@latest

# Update Nuclei and Nuclei-Templates
RUN nuclei -update
RUN nuclei -update-templates

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
