FROM python:3.11-slim

WORKDIR /app

# Prevent Python from writing pyc files and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies
# nodejs/npm are required so deterministic package-manager operations (npm install
# <pkg>@<version>) can update package.json/package-lock.json instead of the AI
# model hand-editing lockfiles.
# docker.io provides the `docker` CLI only — the daemon is never started here.
# The container talks to the *host's* Docker engine via the socket mounted in
# docker-compose.yml (docker-outside-of-docker), launching isolated sandbox
# containers for Phase 4 verification instead of executing untrusted repo code
# in-process.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    git \
    nodejs \
    npm \
    docker-cli \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
