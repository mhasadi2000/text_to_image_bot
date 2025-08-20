# Use Python 3.11 slim image as base
FROM python:3.11-slim

# Set working directory in container
WORKDIR /app

# Install system dependencies for PIL and font handling
RUN apt-get update && apt-get install -y \
    gcc \
    libjpeg-dev \
    zlib1g-dev \
    libfreetype6-dev \
    liblcms2-dev \
    libwebp-dev \
    tcl8.6-dev \
    tk8.6-dev \
    python3-tk \
    libharfbuzz-dev \
    libfribidi-dev \
    libxcb1-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY simple_bot.py .
COPY fonts/ ./fonts/
COPY image/ ./image/

# Create output directory for generated images
RUN mkdir -p /app/output

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Expose port (not strictly necessary for Telegram bot, but good practice)
EXPOSE 8000

# Health check to ensure bot is running
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import os, requests; requests.get('https://api.telegram.org/bot' + os.getenv('TELEGRAM_BOT_TOKEN', '') + '/getMe', timeout=5) if os.getenv('TELEGRAM_BOT_TOKEN') else exit(1)" || exit 1

# Run the bot
CMD ["python", "simple_bot.py"]
