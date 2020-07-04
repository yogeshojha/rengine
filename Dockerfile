# Base image
FROM python:3

# Labels and Credits
LABEL \
    name="reNgine" \
    author="Yogesh Ojha <yogesh.ojha11@gmail.com>" \
    description="reNgine is a automated pipeline of recon process, useful for information gathering during web application penetration testing."

# Environment vars
ENV PYTHONUNBUFFERED 1
ARG DEBIAN_FRONTEND=noninteractive

RUN apt update -y && apt install -y \
  build-essential \
  chromium \
  libpq-dev \
  nmap

# Copy requirements
COPY ./requirements.txt /tmp/requirements.txt
RUN pip3 install -r /tmp/requirements.txt
RUN mkdir /app
WORKDIR /app

# Copy source code
COPY . /app/
RUN chmod +x /app/tools/get_subdomain.sh
RUN chmod +x /app/tools/get_dirs.sh
