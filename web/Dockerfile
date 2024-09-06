# Base image
FROM ubuntu:22.04

# Args and Environment Variables
ARG GECKOVERSION=0.33.0
ARG GOVERSION=1.21.5
ENV DEBIAN_FRONTEND="noninteractive"
ENV DATABASE="postgres"
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
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
    && apt update -y

# Install Go
RUN ARCH=$(dpkg --print-architecture) \
     && curl -s -L -o /tmp/go.tar.gz https://go.dev/dl/go${GOVERSION}.linux-${ARCH}.tar.gz \
     && tar -xzC /usr/local -f /tmp/go.tar.gz \
     && rm /tmp/go.tar.gz

# Install Gecko Driver
RUN ARCH=$(dpkg --print-architecture) \
    && if [ "${ARCH}" = "arm64" ]; then \
      GECKOPATH="geckodriver-v${GECKOVERSION}-linux-aarch64.tar.gz"; \
    elif [ "${ARCH}" = "amd64" ]; then \
      GECKOPATH="geckodriver-v${GECKOVERSION}-linux64.tar.gz"; \
    fi \
    && wget https://github.com/mozilla/geckodriver/releases/download/v${GECKOVERSION}/${GECKOPATH} \
    && tar -xvf ${GECKOPATH} \
    && rm ${GECKOPATH} \
    && mv geckodriver /usr/bin

# Install Rust
RUN set -e; curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"
RUN pip3 install maturin

# Install Go packages
WORKDIR /usr/src/app
ENV GO111MODULE=on
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
    xargs -L1 go install -ldflags="-s -w" -v && \
    rm -rf /go/pkg/* && rm -rf /root/.cache/go-build

# Update Nuclei and Nuclei-Templates
RUN nuclei -update-templates

# Copy requirements
COPY ./requirements.txt /tmp/requirements.txt
RUN pip3 install --upgrade setuptools==72.1.0
RUN pip3 install -r /tmp/requirements.txt --no-cache-dir

# install eyewitness
RUN pip3 install --no-cache-dir fuzzywuzzy \
    selenium==4.9.1 \
    python-Levenshtein \
    pyvirtualdisplay \
    netaddr

# Copy source code
COPY . /usr/src/app/
