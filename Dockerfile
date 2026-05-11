# ══════════════════════════════════════════════════════════════════
# Stage 1 — Build React frontend
# ══════════════════════════════════════════════════════════════════
FROM node:20-slim AS frontend-builder

WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build


# ══════════════════════════════════════════════════════════════════
# Stage 2 — Python application
# ══════════════════════════════════════════════════════════════════
FROM python:3.11-slim

# ── System packages ─────────────────────────────────────────────────
# Tesseract OCR + Khmer language pack + PDF tools + OpenCV headless deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-khm \
    tesseract-ocr-eng \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    poppler-utils \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# ── Python packages ─────────────────────────────────────────────────
WORKDIR /app
COPY requirements.txt ./

# Install headless OpenCV (no GUI needed on server) + gunicorn
RUN pip install --no-cache-dir \
    flask>=3.0 \
    flask-cors \
    pytesseract \
    pdf2image \
    opencv-python-headless \
    Pillow \
    numpy \
    google-genai \
    anthropic \
    python-docx \
    gunicorn

# ── Application code ─────────────────────────────────────────────────
COPY app.py ocr_preprocess.py evaluate_metrics.py ./
COPY templates/ templates/
COPY static/   static/

# ── Built React frontend ─────────────────────────────────────────────
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# ── Runtime setup ────────────────────────────────────────────────────
RUN mkdir -p uploads

# Non-root user (security best practice)
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

ENV PORT=8080
ENV FLASK_ENV=production
EXPOSE 8080

# ── Start server ─────────────────────────────────────────────────────
# gthread worker: supports SSE (streaming) with multiple threads
CMD ["gunicorn", \
     "--bind", "0.0.0.0:8080", \
     "--workers", "1", \
     "--worker-class", "gthread", \
     "--threads", "4", \
     "--timeout", "300", \
     "--keep-alive", "75", \
     "--access-logfile", "-", \
     "app:app"]
