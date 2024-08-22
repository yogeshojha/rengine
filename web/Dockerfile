# build stage from ubuntu
FROM ubuntu:22.04 AS builder

ARG GECKOVERSION=0.33.0
ARG GOVERSION=1.21.5

# env vars
ENV DEBIAN_FRONTEND="noninteractive" \
    DATABASE="postgres" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    GOROOT="/usr/local/go" \
    GOPATH=$HOME/go \
    PATH="${PATH}:${GOROOT}/bin:${GOPATH}/bin"

# essential packages during build, we can remove some of them later
RUN apt-get update && apt-get install -y software-properties-common \
    && add-apt-repository ppa:mozillateam/ppa \
    && apt-get update && apt-get install -y \
    python3.10 \
    python3-dev \
    python3-pip \
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
    && rm -rf /var/lib/apt/lists/*

# Install Go
RUN ARCH=$(dpkg --print-architecture) \ 
    && curl -L https://go.dev/dl/go${GOVERSION}.linux-${ARCH}.tar.gz | tar -xzC /usr/local

# Install Geckodriver
RUN ARCH=$(dpkg --print-architecture) \ 
    && if [ "${ARCH}" = "arm64" ]; then \
      GECKOPATH="geckodriver-v${GECKOVERSION}-linux-aarch64.tar.gz"; \
    elif [ "${ARCH}" = "amd64" ]; then \
      GECKOPATH="geckodriver-v${GECKOVERSION}-linux64.tar.gz"; \
    else \
      echo "reNgine not supported, encountered unknown architecture: ${ARCH}" \
      && exit 1; \
    fi \
    && wget https://github.com/mozilla/geckodriver/releases/download/v${GECKOVERSION}/${GECKOPATH} \
    && tar -xvf ${GECKOPATH} \
    && rm ${GECKOPATH} \
    && mv geckodriver /usr/bin

# Install Rust for orjson
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"
RUN pip3 install maturin

# Install Go tools
ENV GO111MODULE=on 
RUN go install -v \
    github.com/jaeles-project/gospider@latest \
    github.com/tomnomnom/gf@latest \
    github.com/tomnomnom/unfurl@latest \
    github.com/tomnomnom/waybackurls@latest \
    github.com/projectdiscovery/httpx/cmd/httpx@latest \
    github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest \
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
    github.com/sa7mon/s3scanner@latest

# update nuclei templates
RUN nuclei -update-templates

# python deps
COPY ./requirements.txt /tmp/requirements.txt
RUN pip3 install --upgrade setuptools==72.1.0 \
    && pip3 install -r /tmp/requirements.txt --no-cache-dir \
    && pip3 install --no-cache-dir fuzzywuzzy \
    selenium==4.9.1 \
    python-Levenshtein \
    pyvirtualdisplay \
    netaddr

# final build stage
FROM ubuntu:22.04

ARG GECKOVERSION=0.33.0
ARG GOVERSION=1.21.5

# Labels and Credits
LABEL \
    name="reNgine" \
    author="Yogesh Ojha <yogesh.ojha11@gmail.com>" \
    description="reNgine is a automated pipeline of recon process, useful for information gathering during web application penetration testing."

# env vars
ENV DEBIAN_FRONTEND="noninteractive" \
    DATABASE="postgres" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    GOROOT="/usr/local/go" \
    GOPATH=$HOME/go \
    PATH="${PATH}:${GOROOT}/bin:${GOPATH}/bin"

# we now copy the built binaries and dependencies from the builder stage
COPY --from=builder /usr/local /usr/local
COPY --from=builder /usr/bin/geckodriver /usr/bin/geckodriver
COPY --from=builder /root/.cargo /root/.cargo
COPY --from=builder /root/go /root/go

# runtime packages
RUN apt-get update && apt-get install -y software-properties-common \
    && add-apt-repository ppa:mozillateam/ppa \
    && apt-get update && apt-get install -y \
    python3.10 \
    python3-pip \
    libpq-dev \
    geoip-bin \
    geoip-database \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libpcap-dev \
    netcat \
    nmap \
    x11-utils \
    xvfb \
    curl \
    python3-netaddr \
    && rm -rf /var/lib/apt/lists/*

# Make directory for app
WORKDIR /usr/src/app

# Copy source code
COPY . /usr/src/app/