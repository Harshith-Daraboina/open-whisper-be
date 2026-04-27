# Use a slim Python image
FROM python:3.11-slim

# Install system dependencies for audio processing
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Expose the port FastAPI will run on
EXPOSE 7860

# Start the application using uvicorn
# We use the PORT environment variable provided by Render/HF
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-7860}
