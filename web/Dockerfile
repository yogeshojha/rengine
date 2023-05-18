# Base image
FROM ubuntu:20.04

# Labels and Credits
LABEL \
    name="ajta" \
    author="disciple" \
    description="ajta is a automated pipeline of recon process, useful for information gathering during web application penetration testing."

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
    xvfb \
    python3-cffi \
    python3-brotli \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    geoip-bin \
    geoip-database


# Download and install go 1.20
RUN wget -O go1.20.linux-amd64.tar.gz  https://cdna.p30download.ir/p30dl-software/Go.v1.19.5.Linux.x64_p30download.com.tar.gz
RUN tar -xvf go1.20.linux-amd64.tar.gz
RUN rm go1.20.linux-amd64.tar.gz
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
RUN go install -v github.com/hakluke/hakrawler@latest

RUN GO111MODULE=on go install -v -v github.com/bp0lr/gauplus@latest

RUN GO111MODULE=on go install -v github.com/jaeles-project/gospider@latest

RUN apt install unzip -y
RUN wget https://github.com/owasp-amass/amass/releases/download/v3.23.2/amass_Linux_amd64.zip
RUN unzip  amass_Linux_amd64.zip
RUN mv amass_Linux_amd64/amass /usr/local/go/bin
RUN rm -rf amass*

RUN go install -v github.com/ffuf/ffuf@latest

RUN go install -v github.com/tomnomnom/assetfinder@latest
RUN GO111MODULE=on go install -v github.com/tomnomnom/gf@latest
RUN GO111MODULE=on go install -v github.com/tomnomnom/unfurl@latest
RUN GO111MODULE=on go install -v github.com/tomnomnom/waybackurls@latest


#RUN GO111MODULE=on go install -v github.com/projectdiscovery/httpx/cmd/httpx@latest
RUN wget https://github.com/projectdiscovery/httpx/releases/download/v1.3.1/httpx_1.3.1_linux_amd64.zip
RUN unzip httpx_1.3.1_linux_amd64.zip
RUN mv httpx /usr/local/go/bin
RUN rm -rf httpx*



#RUN GO111MODULE=on go install -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest
RUN wget https://github.com/projectdiscovery/subfinder/releases/download/v2.5.8/subfinder_2.5.8_linux_amd64.zip
RUN unzip subfinder_2.5.8_linux_amd64.zip
RUN mv subfinder /usr/local/go/bin
RUN rm -rf subfinder*


#RUN GO111MODULE=on go install -v github.com/projectdiscovery/nuclei/v2/cmd/nuclei@latest
RUN wget https://github.com/projectdiscovery/nuclei/releases/download/v2.9.4/nuclei_2.9.4_linux_amd64.zip
RUN unzip nuclei_2.9.4_linux_amd64.zip
RUN mv nuclei /usr/local/go/bin
RUN rm -rf nuclei*



#RUN GO111MODULE=on go install -v github.com/projectdiscovery/naabu/v2/cmd/naabu@latest
RUN wget https://github.com/projectdiscovery/naabu/releases/download/v2.1.6/naabu_2.1.6_linux_amd64.zip
RUN unzip naabu_2.1.6_linux_amd64.zip
RUN mv naabu /usr/local/go/bin
RUN rm -rf naabu*

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

# httpx seems to have issue, use alias instead!!!
RUN echo 'alias httpx="/go/bin/httpx"' >> ~/.bashrc
