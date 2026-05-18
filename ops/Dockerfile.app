FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# OCR (Tesseract) + poppler for pdf2image + libs requeridas por Pillow.
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-spa \
    tesseract-ocr-eng \
    poppler-utils \
    libjpeg62-turbo \
    zlib1g \
    curl \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy source first so pip install -e finds the package layout. The pyproject
# declares src/repse as the package; the editable install creates a .pth that
# points back into /app/src.
COPY backend /app
RUN pip install --upgrade pip && pip install -e ".[dev]"

RUN useradd --create-home --uid 1000 app && chown -R app:app /app
USER app

EXPOSE 8000
CMD ["uvicorn", "repse.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
