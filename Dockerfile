FROM python:3.12.3-slim

# Set working directory
WORKDIR /app

# Install system dependencies (ffmpeg, audio libs, build tools)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    libsndfile1-dev \
    libopenblas-dev \
    liblapack-dev \
    libblas-dev \
    gfortran \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Chinese fonts
RUN cat > /etc/apt/sources.list.d/debian-bookworm-full.list <<EOF
deb http://mirrors.aliyun.com/debian/ bookworm main contrib non-free non-free-firmware
deb http://mirrors.aliyun.com/debian/ bookworm-updates main contrib non-free non-free-firmware
deb http://mirrors.aliyun.com/debian/ bookworm-backports main contrib non-free non-free-firmware
deb http://mirrors.aliyun.com/debian-security bookworm-security main contrib non-free non-free-firmware
EOF
RUN apt-get update && apt-get install -y fonts-noto-cjk && fc-cache -fv && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml ./
COPY .env.prod ./.env
COPY app ./app
COPY scripts ./scripts

# Install Python dependencies
# Note: torch/torchaudio are large; consider pre-building or using specific versions for CPU/GPU optimization
RUN pip install --no-cache-dir -e .

# Create storage directory for mounting
RUN mkdir -p /app/storage

# Expose port for FastAPI
EXPOSE 8000

# Default command (can be overridden in docker-compose)
CMD ["python", "./app/main.py"]


