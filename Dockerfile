FROM ubuntu:20.04

ARG DEBIAN_FRONTEND=noninteractive

RUN apt update -y && apt install -y \
  build-essential \
  curl \
  python3.8 \
  python3-dev \
  python3-pip \
  wget \
  libpq-dev \
  nmap

RUN curl -LO https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
RUN apt-get install -y ./google-chrome-stable_current_amd64.deb
RUN rm google-chrome-stable_current_amd64.deb

COPY ./requirements.txt /tmp/requirements.txt
RUN pip3 install -r /tmp/requirements.txt
RUN mkdir /app
WORKDIR /app
COPY . /app/
RUN chmod +x /app/tools/get_subdomain.sh
