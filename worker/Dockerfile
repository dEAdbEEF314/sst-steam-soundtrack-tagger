FROM python:3.11-slim

# ---- system deps ----
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libchromaprint-tools \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ---- uv install ----
RUN pip install --no-cache-dir uv

# ---- workdir ----
WORKDIR /app

# ---- python deps ----
COPY requirements.txt .
RUN uv pip install --system -r requirements.txt

# ---- test fpcalc ----
RUN which fpcalc && fpcalc -version

# ---- copy src ----
COPY . .

# ---- default command ----
CMD ["prefect", "worker", "start", "--pool", "default"]
