# Base image
FROM --platform=linux/amd64 ubuntu:22.04

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
ENV GOROOT="/usr/local/go"
ENV GOPATH=$HOME/go
ENV PATH="${PATH}:${GOROOT}/bin:${GOPATH}/bin"

# Install Python
RUN apt update -y && \
    apt update -y && \
    apt install -y \
    python3.10 \
    python3-dev \
    python3-pip

# Install essential packages
RUN apt install -y  --no-install-recommends \
    build-essential \
    cmake \
    geoip-bin \
    geoip-database \
    gcc \
    git \
    libpq-dev \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libpcap-dev \
    netcat \
    nmap \
    x11-utils \
    xvfb \
    wget \
    curl \
    python3-netaddr \
    software-properties-common

RUN add-apt-repository ppa:mozillateam/ppa

# Download and install go 1.20
RUN wget https://golang.org/dl/go1.21.4.linux-amd64.tar.gz
RUN tar -xvf go1.21.4.linux-amd64.tar.gz
RUN rm go1.21.4.linux-amd64.tar.gz
RUN mv go /usr/local

# Download geckodriver
RUN wget https://github.com/mozilla/geckodriver/releases/download/v0.32.0/geckodriver-v0.32.0-linux64.tar.gz
RUN tar -xvf geckodriver-v0.32.0-linux64.tar.gz
RUN rm geckodriver-v0.32.0-linux64.tar.gz
RUN mv geckodriver /usr/bin

# Make directory for app
WORKDIR /usr/src/app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Download Go packages
RUN go install -v github.com/jaeles-project/gospider@latest
RUN go install -v github.com/tomnomnom/gf@latest
RUN go install -v github.com/tomnomnom/unfurl@latest
RUN go install -v github.com/tomnomnom/waybackurls@latest
RUN go install -v github.com/projectdiscovery/httpx/cmd/httpx@latest
RUN go install -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest
RUN go install -v github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest
RUN go install -v github.com/projectdiscovery/naabu/v2/cmd/naabu@latest
RUN go install -v github.com/hakluke/hakrawler@latest
RUN go install -v github.com/lc/gau/v2/cmd/gau@latest
RUN go install -v github.com/jaeles-project/gospider@latest
RUN go install -v github.com/owasp-amass/amass/v3/...@latest
RUN go install -v github.com/ffuf/ffuf@latest
RUN go install -v github.com/projectdiscovery/tlsx/cmd/tlsx@latest
RUN go install -v github.com/hahwul/dalfox/v2@latest
RUN go install -v github.com/projectdiscovery/katana/cmd/katana@latest
RUN go install -v github.com/dwisiswant0/crlfuzz/cmd/crlfuzz@latest
RUN go install -v github.com/sa7mon/s3scanner@latest

# Update Nuclei and Nuclei-Templates
RUN nuclei -update
RUN nuclei -update-templates

# Update project discovery tools
RUN httpx -up
RUN naabu -up
RUN subfinder -up
RUN tlsx -up
RUN katana -up

# Copy requirements
COPY ./requirements.txt /tmp/requirements.txt
RUN pip3 install --upgrade setuptools pip && \
    pip3 install -r /tmp/requirements.txt


# install eyewitness

RUN python3 -m pip install fuzzywuzzy \
    selenium==4.9.1 \
    python-Levenshtein \
    pyvirtualdisplay \
    netaddr

# Copy source code
COPY . /usr/src/app/

# httpx seems to have issue, use alias instead!!!
RUN echo 'alias httpx="/go/bin/httpx"' >> ~/.bashrc
