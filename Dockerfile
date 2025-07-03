# Dockerfile
FROM python:3.12-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
  PYTHONPATH=/app \
  IS_PRODUCTION=true \
  PORT=8000

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
  curl \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY src /app/src
COPY credentials.json /app/credentials.json

# Expose ports
EXPOSE 8501 8000

# Start script
COPY start.sh /app/
RUN chmod +x /app/start.sh

CMD ["/app/start.sh"]
