# Base image: small Alpine Linux with Python 3.11 installed
FROM python:3.11-alpine

# Show logs immediately; don't create .pyc files
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Work inside /app in the container
WORKDIR /app

# Install dependencies first (cached when only code changes)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY server.py store.py ./

# The port the server listens on
EXPOSE 8080

# Start the server when the container starts
CMD ["python", "server.py", "--host", "0.0.0.0", "--port", "8080"]