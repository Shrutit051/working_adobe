# Dockerfile

# Specify the base platform to ensure compatibility
FROM python:3.10-slim

# Install system dependencies required for PyMuPDF
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    libmupdf-dev \
    libfreetype6-dev \
    libharfbuzz-dev \
    libopenjp2-7-dev \
    libjbig2dec0-dev \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Copy and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy your application code
COPY process_pdfs.py .

# Define the command to run the application
CMD ["python", "process_pdfs.py"]