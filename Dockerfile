# Base image
FROM python:3

# Labels and Credits
LABEL \
    name="reNgine" \
    author="Yogesh Ojha <yogesh.ojha11@gmail.com>" \
    description="reNgine is a automated pipeline of recon process, useful for information gathering during web application penetration testing."

ARG DEBIAN_FRONTEND=noninteractive

RUN apt update -y && apt install -y \
  build-essential \
  chromium \
  libpq-dev \
  nmap

# Copy requirements
COPY ./requirements.txt /tmp/requirements.txt
RUN pip3 install -r /tmp/requirements.txt

# Download and install go 1.13
RUN wget https://dl.google.com/go/go1.13.6.linux-amd64.tar.gz
RUN tar -zxvf go1.13.6.linux-amd64.tar.gz -C /usr/local
RUN rm o1.13.6.linux-amd64.tar.gz -f

# Environment vars
ENV PYTHONUNBUFFERED 1
ENV GOROOT="/usr/local/go"
ENV GOPATH="/root/go"
ENV PATH="${PATH}:${GOROOT}/bin"
ENV PATH="${PATH}:${GOPATH}/bin"

# Download Go packages
RUN go get -u github.com/tomnomnom/assetfinder

RUN GO111MODULE=on go get -u -v github.com/projectdiscovery/httpx/cmd/httpx \
    github.com/projectdiscovery/naabu/cmd/naabu \
    github.com/projectdiscovery/subfinder/cmd/subfinder \
    github.com/lc/gau



# Make directory for app
RUN mkdir /app
WORKDIR /app

# Copy source code
COPY . /app/

RUN chmod +x /app/tools/get_subdomain.sh
RUN chmod +x /app/tools/get_dirs.sh
