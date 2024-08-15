# Base image
FROM ubuntu:22.04

# Arguments for versions
ARG GECKOVERSION=0.35.0
ARG GOVERSION=1.21.5

# Supported architectures
ARG SUPPORTED_ARCH="amd64 arm64 armv6 armv7 armhf i386"

# Labels
LABEL name="reNgine" \
      author="Yogesh Ojha <yogesh.ojha11@gmail.com>" \
      description="reNgine is an automated pipeline for recon processes, useful for information gathering during web application penetration testing."

# Environment variables
ENV DEBIAN_FRONTEND="noninteractive" \
    DATABASE="postgres" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOME="/root" \
    GOROOT="/usr/local/go" \
    GOPATH="/root/go" \
    PATH="$PATH:/usr/local/go/bin:/root/go/bin" \
    GO111MODULE=on

# Install required packages and add Mozilla Team PPA
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
    && apt update -y

# Install Go based on architecture
RUN ARCH=$(dpkg --print-architecture) \
    && case "$ARCH" in \
      arm64) GOFILE="go${GOVERSION}.linux-arm64.tar.gz" ;; \
      amd64) GOFILE="go${GOVERSION}.linux-amd64.tar.gz" ;; \
      armhf|armv6|armv7) GOFILE="go${GOVERSION}.linux-armv6l.tar.gz" ;; \
      i386) GOFILE="go${GOVERSION}.linux-386.tar.gz" ;; \
      *) echo "Unsupported architecture: $ARCH"; exit 1 ;; \
    esac \
    && wget https://go.dev/dl/${GOFILE} \
    && tar -xvf ${GOFILE} -C /usr/local \
    && rm ${GOFILE}

# Install Geckodriver based on architecture
RUN ARCH=$(dpkg --print-architecture) \
    && case "$ARCH" in \
      arm64) GECKOPATH="geckodriver-v${GECKOVERSION}-linux-aarch64.tar.gz" \
             GECKOREPO="https://github.com/khulnasoft-lab/geckodriver/releases/download/v${GECKOVERSION}/${GECKOPATH}" ;; \
      armv7l) GECKOPATH="geckodriver-v${GECKOVERSION}-linux-armv7l.tar.gz" \
             GECKOREPO="https://github.com/khulnasoft-lab/geckodriver/releases/download/v${GECKOVERSION}/${GECKOPATH}" ;; \
      amd64) GECKOPATH="geckodriver-v${GECKOVERSION}-linux64.tar.gz" ;; \
      armhf|armv6|i386) GECKOPATH="geckodriver-v${GECKOVERSION}-linux32.tar.gz" ;; \
      *) echo "Unsupported architecture: $ARCH"; exit 1 ;; \
    esac \
    && wget ${GECKOREPO:-https://github.com/mozilla/geckodriver/releases/download/v${GECKOVERSION}/${GECKOPATH}} \
    && tar -xvf ${GECKOPATH} -C /usr/local/bin \
    && rm ${GECKOPATH}

# Install Rust for orjson
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y \
    && echo "source $HOME/.cargo/env" >> $HOME/.bashrc

ENV PATH="/root/.cargo/bin:$PATH"

# Install Maturin for Python bindings
RUN pip3 install maturin

# Set working directory
WORKDIR /usr/src/app

# Install Go tools
RUN printf "\
    github.com/jaeles-project/gospider@latest\n\
    github.com/tomnomnom/gf@latest\n\
    github.com/tomnomnom/unfurl@latest\n\
    github.com/tomnomnom/waybackurls@latest\n\
    github.com/projectdiscovery/httpx/cmd/httpx@latest\n\
    github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest\n\
    github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest\n\
    github.com/projectdiscovery/naabu/v2/cmd/naabu@latest\n\
    github.com/hakluke/hakrawler@latest\n\
    github.com/lc/gau/v2/cmd/gau@latest\n\
    github.com/owasp-amass/amass/v3/...@latest\n\
    github.com/ffuf/ffuf@latest\n\
    github.com/projectdiscovery/tlsx/cmd/tlsx@latest\n\
    github.com/hahwul/dalfox/v2@latest\n\
    github.com/projectdiscovery/katana/cmd/katana@latest\n\
    github.com/dwisiswant0/crlfuzz/cmd/crlfuzz@latest\n\
    github.com/sa7mon/s3scanner@latest\n" | \
    xargs -L1 go install -ldflags="-s -w" -v \
    && rm -rf /go/pkg/* /root/.cache/go-build

# Update Nuclei and Nuclei-Templates
RUN nuclei -update-templates

# Install Python dependencies
COPY ./requirements.txt /tmp/requirements.txt
RUN pip3 install --upgrade setuptools==72.1.0 \
    && pip3 install -r /tmp/requirements.txt --no-cache-dir

# Install eyewitness dependencies
RUN pip3 install --no-cache-dir \
    fuzzywuzzy selenium==4.9.1 python-Levenshtein pyvirtualdisplay netaddr

# Copy application code
COPY . /usr/src/app/
