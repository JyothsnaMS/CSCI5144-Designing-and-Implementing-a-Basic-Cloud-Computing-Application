# 1. Base image: small Alpine Linux with Python 3.11 already installed
FROM python:3.11-alpine

# 2. Settings: print logs immediately, don't write .pyc files
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# 3. Work inside /app in the container
WORKDIR /app

# 4. Install dependencies first (cached unless requirements.txt changes)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy all application files: server.py, store.py, router.py, hash_ring.py, benchmark.py.
#    The same image runs a store, the router or the benchmark; docker-compose.yml picks which.
COPY *.py ./

# 6. Document the ports: 8080 for a store, 8000 for the router
EXPOSE 8080 8000

# 7. Default: start one store. 0.0.0.0 makes it reachable from other containers and the host
CMD ["python", "server.py", "--host", "0.0.0.0", "--port", "8080"]