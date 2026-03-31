FROM python:3.11-slim

# ---- system deps ----
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ---- uv install ----
RUN pip install --no-cache-dir uv

# ---- workdir ----
WORKDIR /app

# ---- python deps ----
COPY requirements.txt .
RUN uv pip install --system -r requirements.txt

# ---- copy src ----
COPY src/ ./src/
COPY config.yaml .

# ---- PYTHONPATH ----
ENV PYTHONPATH=/app/src

# ---- default entry ----
ENTRYPOINT ["python", "/app/src/main.py"]
