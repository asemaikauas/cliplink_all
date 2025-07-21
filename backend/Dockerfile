# FastAPI Backend Dockerfile with conda-forge OpenCV for native AV1 support
FROM continuumio/miniconda3:latest

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Install system dependencies (keeping essential ones)
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
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 appuser

# Set work directory
WORKDIR /app

# Update conda and install OpenCV with native AV1 support from conda-forge
RUN conda update -n base -c conda-forge conda && \
    conda install -c conda-forge python=3.12 opencv libopencv py-opencv && \
    conda clean -afy

# Copy requirements (excluding opencv-python since we installed it via conda)
COPY requirements.txt ./

# Install remaining Python dependencies via pip (excluding opencv packages) 
# Note: apify-client is included in requirements.txt for YouTube downloads
RUN sed '/opencv-python/d' requirements.txt > requirements_no_opencv.txt && \
    pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements_no_opencv.txt && \
    rm requirements_no_opencv.txt

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