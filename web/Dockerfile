# Base image
FROM ubuntu:22.04

ARG version=0.33.0
ARG geckodriver_amd=geckodriver-v${version}-linux64.tar.gz
ARG geckodriver_arm=geckodriver-v${version}-linux-aarch64.tar.gz

ARG go_version=1.21.5
ARG go_amd=go${go_version}.linux-amd64.tar.gz
ARG go_arm=go${go_version}.linux-arm64.tar.gz


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

RUN  ARCH=$(dpkg --print-architecture) \
    && if [ "${ARCH}" = "arm64" ]; then \
        wget https://go.dev/dl/${go_arm} \
        && tar -xvf ${go_arm} \
        && rm ${go_arm} \
        && mv go /usr/local; \
      elif [ "${ARCH}" = "amd64" ]; then \
        wget https://go.dev/dl/${go_amd} \
        && tar -xvf ${go_amd} \
        && rm ${go_amd} \
        && mv go /usr/local; \
      else \
        echo "Unknown architecture: $ARCH" ; \
        exit 1; \
      fi



RUN ARCH=$(dpkg --print-architecture) \
    && if [ "${ARCH}" = "arm64" ]; then \
      wget https://github.com/mozilla/geckodriver/releases/download/v${version}/${geckodriver_arm} \
      && tar -xvf ${geckodriver_arm} \
      && rm ${geckodriver_arm} \
      && mv geckodriver /usr/bin; \
    elif [ "${ARCH}" = "amd64" ]; then \
      wget https://github.com/mozilla/geckodriver/releases/download/v${version}/${geckodriver_amd} \
      && tar -xvf ${geckodriver_amd} \
      && rm ${geckodriver_amd} \
      && mv geckodriver /usr/bin; \
    else \
      echo "Unknown architecture: $ARCH" ; \
    exit 1; \
  fi


# Make directory for app
WORKDIR /usr/src/app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Download Go packages



RUN ARCH=$(dpkg --print-architecture) \
    && if [[ "$ARCH" = "arm64" || "$ARCH" = "amd64" ]]; then
        GOARCH=$ARCH go install -v github.com/jaeles-project/gospider@latest \
        && GOARCH=$ARCH go install -v github.com/tomnomnom/gf@latest \
        && GOARCH=$ARCH go install -v github.com/tomnomnom/unfurl@latest \
        && GOARCH=$ARCH go install -v github.com/tomnomnom/waybackurls@latest \
        && GOARCH=$ARCH go install -v github.com/projectdiscovery/httpx/cmd/httpx@latest \
        && GOARCH=$ARCH go install -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest \
        && GOARCH=$ARCH go install -v github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest \
        && GOARCH=$ARCH go install -v github.com/projectdiscovery/naabu/v2/cmd/naabu@latest \
        && GOARCH=$ARCH go install -v github.com/lc/gau/v2/cmd/gau@latest \
        && GOARCH=$ARCH go install -v github.com/jaeles-project/gospider@latest \
        && GOARCH=$ARCH go install -v github.com/owasp-amass/amass/v3/...@latest \
        && GOARCH=$ARCH go install -v github.com/ffuf/ffuf@latest \
        && GOARCH=$ARCH go install -v github.com/projectdiscovery/tlsx/cmd/tlsx@latest \
        && GOARCH=$ARCH go install -v github.com/hahwul/dalfox/v2@latest \
        && GOARCH=$ARCH go install -v github.com/projectdiscovery/katana/cmd/katana@latest \
        && GOARCH=$ARCH go install -v github.com/dwisiswant0/crlfuzz/cmd/crlfuzz@latest \
        && GOARCH=$ARCH go install -v github.com/sa7mon/s3scanner@latest; \
    else \
        echo "Unknown architecture: $ARCH" ; \
        exit 1; \
    fi


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
