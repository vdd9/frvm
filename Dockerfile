FROM python:3.12-slim

WORKDIR /app

# Dependencies for bitarray compilation + ffmpeg for thumbnails
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    libc6-dev \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Frontend is included in the image
RUN mkdir -p /app/frontend/static /data

EXPOSE 8000

CMD ["python", "main.py", "--data=/data"]
