FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    ffmpeg \
    libsndfile1 \
    git \
    portaudio19-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.docker.txt .
RUN pip install --no-cache-dir -r requirements.docker.txt

RUN python -m spacy download en_core_web_sm

COPY . .

EXPOSE 5050

CMD ["python", "app.py"]
