FROM ubuntu:20.04
RUN mkdir /app
WORKDIR /app

RUN apt update -y && apt install -y \
  build-essential \
  python3.8 \
  python3-dev \
  python3-pip \
  wget

COPY requirements.txt /app/
RUN pip3 install -r requirements.txt
COPY . /app/
