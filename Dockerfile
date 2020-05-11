FROM ubuntu:20.04

RUN apt update -y && apt install -y \
  build-essential \
  python3.8 \
  python3-dev \
  python3-pip \
  wget \
  libpq-dev

COPY ./requirements.txt /tmp/requirements.txt
RUN pip3 install -r /tmp/requirements.txt
RUN mkdir /app
WORKDIR /app
COPY . /app/
