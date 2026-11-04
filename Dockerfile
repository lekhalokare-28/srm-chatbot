# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir groq schedule

# Copy all project files
COPY . .

# Run scraper and build vector store on first launch
RUN mkdir -p data

# Expose backend port
EXPOSE 8000

# Start script
CMD ["python3", "start.py"]
