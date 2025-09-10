FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /code

# Install system deps required to build some Python packages
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       build-essential gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements first (layer caching)
COPY requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir -r /code/requirements.txt \
    && rm -rf /root/.cache/pip

# Copy project
COPY . /code

# Ensure entrypoint is executable
RUN ["/bin/bash", "-lc", "chmod +x /code/docker/entrypoint.sh || true"]

ENTRYPOINT ["/bin/bash", "/code/docker/entrypoint.sh"]
CMD ["web"]
