FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

# System dependencies for dlib, opencv, mysql, audio processing, etc.
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    libopenblas-dev \
    liblapack-dev \
    libx11-dev \
    libgtk-3-dev \
    pkg-config \
    default-libmysqlclient-dev \
    default-mysql-client \
    ffmpeg \
    libsm6 \
    libxext6 \
    portaudio19-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/

RUN pip install --upgrade pip setuptools wheel
RUN pip install dlib==19.24.1
RUN pip install -r requirements.txt

COPY . /app/
