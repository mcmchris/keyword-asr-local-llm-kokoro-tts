FROM python:3.13-slim

# libsndfile is required by soundfile; espeak-ng is the phonemiser kokoro-onnx
# falls back to for non-English / unknown words.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libsndfile1 espeak-ng \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Bake the ONNX weights and voices bundle into the image so the container
# boots fully offline. ~200 MB total (fp16 model + voices).
COPY models/ /models/

COPY server.py .

ENV KOKORO_MODEL_DIR=/models \
    KOKORO_PORT=9100

EXPOSE 9100
CMD ["python", "-u", "server.py"]
