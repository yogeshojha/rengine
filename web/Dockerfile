# Base image
FROM ubuntu:22.04

# Args and Environment Variables
ARG GECKOVERSION=0.33.0
ARG GOVERSION=1.21.5
ENV DEBIAN_FRONTEND="noninteractive"
ENV DATABASE="postgres"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV GOROOT="/usr/local/go"
ENV GOPATH=$HOME/go
ENV PATH="${PATH}:${GOROOT}/bin:${GOPATH}/bin"

# Labels and Credits
LABEL \
    name="reNgine" \
    author="Yogesh Ojha <yogesh.ojha11@gmail.com>" \
    description="reNgine is a automated pipeline of recon process, useful for information gathering during web application penetration testing."

# Supported architectures
ARG SUPPORTED_ARCH="amd64 arm64 armv6 armv7 armhf i386 x86_64"


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

# Install essential required packages
RUN ARCH=$(dpkg --print-architecture) \
    && echo "$SUPPORTED_ARCH" | grep -qw "$ARCH" || { \
         echo "Unsupported architecture: $ARCH"; exit 1; \
    } \
    && apt update -y \
    && apt install -y --no-install-recommends \
        python3.10 python3-dev python3-pip \
        build-essential cmake geoip-bin geoip-database \
        gcc git libpq-dev libpango-1.0-0 libpangoft2-1.0-0 \
        libpcap-dev netcat nmap x11-utils xvfb wget curl \
        python3-netaddr software-properties-common \
        gpg-agent \
    && add-apt-repository -y ppa:mozillateam/ppa \
    && apt update -y \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Go
RUN ARCH=$(dpkg --print-architecture) \
     && curl -s -L -o /tmp/go.tar.gz https://go.dev/dl/go${GOVERSION}.linux-${ARCH}.tar.gz \
     && tar -xzC /usr/local -f /tmp/go.tar.gz \
     && rm /tmp/go.tar.gz \
     && rm -rf /usr/local/go/pkg/* /root/.cache/go-build
     
# Install Gecko Driver for multiple architectures
RUN ARCH=$(dpkg --print-architecture) \
    && if [ "${ARCH}" = "arm64" ]; then \
      GECKOPATH="geckodriver-v${GECKOVERSION}-linux-aarch64.tar.gz"; \
    elif [ "${ARCH}" = "amd64" ]; then \
      GECKOPATH="geckodriver-v${GECKOVERSION}-linux64.tar.gz"; \
    elif [ "${ARCH}" = "armhf" ]; then \
      GECKOPATH="geckodriver-v${GECKOVERSION}-linux-armv7l.tar.gz"; \
    elif [ "${ARCH}" = "i386" ]; then \
      GECKOPATH="geckodriver-v${GECKOVERSION}-linux32.tar.gz"; \
    else \
      echo "Unsupported architecture: ${ARCH}"; exit 1; \
    fi \
    && wget https://github.com/mozilla/geckodriver/releases/download/v${GECKOVERSION}/${GECKOPATH} \
    && tar -xvf ${GECKOPATH} \
    && rm ${GECKOPATH} \
    && mv geckodriver /usr/bin

# Install Rust and Maturin for building Python extensions
RUN set -e; curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"
RUN pip3 install maturin

# Make directory for app
WORKDIR /usr/src/app

ENV GO111MODULE=on 
# Install Go packages in a loop for better error handling
RUN packages="\
    github.com/jaeles-project/gospider@latest \
    github.com/tomnomnom/gf@latest \
    github.com/tomnomnom/unfurl@latest \
    github.com/tomnomnom/waybackurls@latest \
    github.com/projectdiscovery/httpx/cmd/httpx@latest \
    github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest \
    github.com/projectdiscovery/chaos-client/cmd/chaos@latest \
    github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest \
    github.com/projectdiscovery/naabu/v2/cmd/naabu@latest \
    github.com/hakluke/hakrawler@latest \
    github.com/lc/gau/v2/cmd/gau@latest \
    github.com/owasp-amass/amass/v3/...@latest \
    github.com/ffuf/ffuf@latest \
    github.com/projectdiscovery/tlsx/cmd/tlsx@latest \
    github.com/hahwul/dalfox/v2@latest \
    github.com/projectdiscovery/katana/cmd/katana@latest \
    github.com/dwisiswant0/crlfuzz/cmd/crlfuzz@latest \
    github.com/sa7mon/s3scanner@latest" \
    && for pkg in $packages; do \
      echo "Installing $pkg"; \
      go install -ldflags="-s -w" "$pkg"; \
    done \
    && rm -rf /go/pkg/* /root/.cache/go-build

# Update Nuclei and Nuclei-Templates
RUN nuclei -update-templates

# update chaos
RUN chaos -update

# Copy requirements
COPY ./requirements.txt /tmp/requirements.txt
RUN pip3 install --upgrade setuptools==72.1.0 \
    && pip3 install -r /tmp/requirements.txt --no-cache-dir

# Install additional Python tools
RUN pip3 install --no-cache-dir fuzzywuzzy \
    selenium==4.9.1 \
    python-Levenshtein \
    pyvirtualdisplay \
    netaddr

# Copy source code
COPY . /usr/src/app/
