# Use official lightweight Python image
FROM python:3.12-slim

# Set working directory inside container
WORKDIR /app

# Copy requirements first (for Docker layer caching)
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY main.py .
COPY app/ app/
COPY key.json .

# Set env var so app knows where to find the key
ENV APIGEE_SA_KEY_PATH=/app/key.json

# Expose port
EXPOSE 8080

# Run the app — PORT env var used by Cloud Run, defaults to 8080
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
