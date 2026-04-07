# Use official lightweight Python image
FROM python:3.12-slim

# Set working directory inside container
WORKDIR /app

# Copy requirements first (for Docker layer caching)
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY apigee_manager.py .

# Expose port
EXPOSE 8000

# Run the app
CMD ["uvicorn", "apigee_manager:app", "--host", "0.0.0.0", "--port", "8000"]
