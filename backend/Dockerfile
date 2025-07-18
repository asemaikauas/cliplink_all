# FastAPI Backend Dockerfile
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Install system dependencies including build tools for Python packages
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libdav1d6 \
    libdav1d-dev \
    libaom3 \
    libaom-dev \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    curl \
    build-essential \
    gcc \
    python3-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*


# Create non-root user
RUN useradd -m -u 1000 appuser

# Set work directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt ./
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code (excluding files listed in .dockerignore)
COPY app/ ./app/
COPY schema.sql ./
COPY migrations/ ./migrations/

# Copy necessary model files specifically
RUN mkdir -p /app/models

# скачиваем модельные файлы из репозитория OpenCV
RUN curl -L --fail https://raw.githubusercontent.com/opencv/opencv/4.x/samples/dnn/face_detector/deploy.prototxt \
    -o /app/models/deploy.prototxt \
    && curl -L --fail https://github.com/opencv/opencv_3rdparty/raw/dnn_samples_face_detector_20170830/res10_300x300_ssd_iter_140000.caffemodel \
    -o /app/models/res10_300x300_ssd_iter_140000_fp16.caffemodel


# Create necessary directories
RUN mkdir -p logs downloads temp_uploads clips thumbnails temp_vertical

# Change ownership to appuser
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"] 