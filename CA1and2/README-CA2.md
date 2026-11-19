# Single-Server Key-Value Store

## Overview

This project implements a single-server key-value store for the CSCI 5144 Cloud Computing course. It exposes an HTTP API for storing, retrieving, updating and deleting key-value pairs.

It demonstrates core cloud computing concepts: concurrent request handling, data persistence, error handling, logging, performance benchmarking and containerization with Docker.

| Assignment | What it covers | Git tag |
|---|---|---|
| Coding Assignment 1 | Key-value store server (this README, all sections except Docker) | `ca1-submission` |
| Coding Assignment 2 | Dockerizing the server (see [Running with Docker](#running-with-docker)) | `ca2-submission` |

## Features

- **PUT / POST:** Create a new key-value pair or update an existing one.
- **GET:** Retrieve the value stored under a key.
- **DELETE:** Remove a key and its value.
- **Health check:** `GET /` reports that the server is running and how many keys it holds.
- **Concurrency:** Storage operations are synchronized with a lock, so concurrent PUT/DELETE requests on the same key are safe.
- **Persistence:** A write-ahead log (WAL), periodic snapshots and startup recovery preserve data across restarts and crashes.
- **Error handling:** Errors are returned as JSON with appropriate HTTP status codes.
- **Logging:** Every request is logged with a timestamp, method, key, status code, client address and latency.
- **Benchmarking:** Throughput and latency are measured with concurrent client threads.
- **Docker support:** The server runs in a lightweight Alpine-based container.
- **Persistent Docker storage:** A named Docker volume preserves data across container removal and recreation.
- **Graceful shutdown:** SIGTERM handling lets `docker stop` save a final snapshot and exit cleanly.

## Technologies

- Python 3.11
- Flask (HTTP routing)
- Waitress (multi-threaded WSGI server)
- pytest (automated tests)
- Requests (benchmark client)
- Docker, with the `python:3.11-alpine` base image
- JSON request and response bodies

## Project Structure

```text
CSCI5144-Designing-and-Implementing-a-Basic-Cloud-Computing-Application/
├── server.py             # HTTP server: API endpoints, validation, logging, signal handling
├── store.py              # Storage: locking, write-ahead log, snapshots, recovery
├── benchmark.py          # Concurrent performance benchmark
├── try_store.py          # Script for trying the storage layer directly
├── requirements.txt      # Python dependencies
├── Dockerfile            # Docker image build instructions
├── .dockerignore         # Files excluded from the Docker build context
├── README.md             # Project documentation
├── tests/
│   ├── test_server.py    # API endpoint tests
│   └── test_store.py     # Storage, concurrency and recovery tests
├── data/                 # Snapshot and WAL files (created at runtime, not committed)
└── logs/                 # Request logs (created at runtime, not committed)
```

## Setup and Installation

Python 3.9 or newer is required. The project was developed and tested with Python 3.11.

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Windows (PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

If PowerShell blocks activation, use the environment's Python directly:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Running the Server Locally

With the virtual environment activated:

```bash
python server.py
```

The server listens on `http://127.0.0.1:8080`. Keep it running and send requests from a second terminal.

Press **Ctrl+C** to stop the server gracefully. The storage layer closes and saves a final snapshot.

### Server Options

| Option | Default | Description |
|---|---|---|
| `--host` | `127.0.0.1` | Address to listen on (`0.0.0.0` accepts connections from other machines and from Docker port mapping) |
| `--port` | `8080` | Server port |
| `--threads` | `8` | Number of worker threads |
| `--data-dir` | `data` | Directory for snapshots and WAL files |
| `--log-dir` | `logs` | Directory for request logs |
| `--snapshot-interval` | `30` | Seconds between background snapshots |
| `--fsync` | Disabled | Force every WAL write to disk for stronger durability |

Example:

```bash
python server.py --port 9000 --fsync
```

## Running with Docker

Docker packages the server together with Python and all its dependencies, so it runs the same way on any machine without installing Python packages on the host.

### Assignment 2 Requirements

| Requirement | How it is met |
|---|---|
| 1. Lightweight base image with Python | `FROM python:3.11-alpine` |
| 2. Application files added to the image | `COPY server.py store.py ./` |
| 3. Dependencies installed in the image | `COPY requirements.txt .` and `RUN pip install --no-cache-dir -r requirements.txt` |
| 4. Server port exposed | `EXPOSE 8080`, published at run time with `-p 8080:8080` |
| 5. Server starts automatically | `CMD ["python", "server.py", "--host", "0.0.0.0", "--port", "8080"]` |

### Prerequisites

- Docker Desktop installed and running ("Engine running").
- Port 8080 free on the host. Stop any locally running `python server.py` first.

### 1. Build the Docker Image

From the project root:

```bash
docker build -t kv-store .
```

This builds an image named `kv-store` from the `Dockerfile`: Python 3.11 on Alpine Linux, the dependencies from `requirements.txt`, and the application files. The resulting image is about 115 MB.

Check that it exists:

```bash
docker images kv-store
```

### 2. Run the Docker Container

```bash
docker run -d --name kv -p 8080:8080 -v kv-data:/app/data kv-store
```

| Option | Purpose |
|---|---|
| `-d` | Run the container in the background (detached) |
| `--name kv` | Name the container `kv` |
| `-p 8080:8080` | Map host port 8080 to container port 8080 |
| `-v kv-data:/app/data` | Mount the named volume `kv-data` for persistent data |
| `kv-store` | The image to run |

Check that it is running:

```bash
docker ps
```

The `kv` container should show `Up` and `0.0.0.0:8080->8080/tcp`. The server needs a moment to start, so wait about 3 seconds before sending the first request.

Inside the container the server binds to `0.0.0.0`, so it accepts connections forwarded through Docker's port mapping. With the default `127.0.0.1` it would only accept connections from inside the container.

### 3. Test the API

**macOS / Linux:**

```bash
curl http://localhost:8080/
curl -X PUT http://localhost:8080/docker-test -H "Content-Type: application/json" -d '{"value":"hello from Docker"}'
curl http://localhost:8080/docker-test
curl -X DELETE http://localhost:8080/docker-test
```

**Windows PowerShell:**

```powershell
Invoke-RestMethod -Method Get -Uri "http://localhost:8080/"
Invoke-RestMethod -Method Put -Uri "http://localhost:8080/docker-test" -ContentType "application/json" -Body '{"value":"hello from Docker"}'
Invoke-RestMethod -Method Get -Uri "http://localhost:8080/docker-test"
Invoke-RestMethod -Method Delete -Uri "http://localhost:8080/docker-test"
```

The benchmark also runs unchanged against the container, from the host:

```bash
python benchmark.py
```

#### Verified results (macOS, Docker Desktop)

| Request | Expected and observed status |
|---|---|
| `GET /` | `200` with `{"keys":0,"status":"running"}` |
| `PUT /course` (new key) | `201` created |
| `PUT /course` (existing key) | `200` updated |
| `GET /course` | `200` with the stored value |
| `DELETE /course` | `200` deleted |
| `GET /course` (after delete) | `404` not found |
| `PUT /x` with an invalid body | `400` bad request |
| `PATCH /x` | `405` method not allowed |

### 4. View Container Logs

```bash
docker logs kv        # all log output
docker logs -f kv     # follow new log lines continuously
```

Every request appears with a timestamp, for example:

```text
2026-10-30 04:53:47,034 INFO operation=PUT key='course' status=201 client=192.168.65.1 latency_ms=0.72
```

`client=192.168.65.1` is the Docker Desktop host address, which confirms the requests came from outside the container through the published port. Timestamps inside the container are in UTC.

To open a shell inside the running container:

```bash
docker exec -it kv sh
ls /app          # server.py, store.py, data/, logs/
ls /app/data     # snapshot.json and wal-N.log files
exit
```

### 5. Stop, Restart and Remove the Container

```bash
docker stop kv      # stop gracefully
docker start kv     # restart the same container
docker rm kv        # remove the stopped container
```

To recreate the container with the same data:

```bash
docker run -d --name kv -p 8080:8080 -v kv-data:/app/data kv-store
```

The named volume `kv-data` is kept when the container is removed. To delete all stored data and start fresh, run `docker rm -f kv` and then `docker volume rm kv-data`.

### 6. Verify Persistent Storage

**macOS / Linux:**

```bash
curl -X PUT http://localhost:8080/survivor -H "Content-Type: application/json" -d '{"value":"still here"}'
docker stop kv
docker rm kv
docker run -d --name kv -p 8080:8080 -v kv-data:/app/data kv-store
sleep 3
curl http://localhost:8080/survivor
```

**Windows PowerShell:**

```powershell
Invoke-RestMethod -Method Put -Uri "http://localhost:8080/survivor" -ContentType "application/json" -Body '{"value":"still here"}'
docker stop kv
docker rm kv
docker run -d --name kv -p 8080:8080 -v kv-data:/app/data kv-store
Start-Sleep -Seconds 3
Invoke-RestMethod -Method Get -Uri "http://localhost:8080/survivor"
```

Result in our test: the brand-new container returned `{"key":"survivor","value":"still here"}`. The data is stored in the named volume, not in the container's writable layer, so it survives container removal.

### 7. Test Crash Recovery

`docker kill` sends SIGKILL, which stops the container immediately without a final snapshot.

**macOS / Linux:**

```bash
curl -X PUT http://localhost:8080/crash2 -H "Content-Type: application/json" -d '{"value":"survives"}'
docker kill kv
docker rm kv
docker run -d --name kv -p 8080:8080 -v kv-data:/app/data kv-store
sleep 3
curl http://localhost:8080/crash2
```

**Windows PowerShell:**

```powershell
Invoke-RestMethod -Method Put -Uri "http://localhost:8080/crash2" -ContentType "application/json" -Body '{"value":"survives"}'
docker kill kv
docker rm kv
docker run -d --name kv -p 8080:8080 -v kv-data:/app/data kv-store
Start-Sleep -Seconds 3
Invoke-RestMethod -Method Get -Uri "http://localhost:8080/crash2"
```

Result in our test: the new container returned `{"key":"crash2","value":"survives"}`. The value was rebuilt from the write-ahead log during startup recovery.

This demonstrates recovery after a process crash. Without `--fsync`, a sudden power loss of the host could still lose the most recent writes.

### 8. Graceful Shutdown

`docker stop kv` sends SIGTERM to the container's main process:

1. The Python signal handler in `server.py` raises `KeyboardInterrupt`.
2. The server's cleanup code calls the storage layer's `close()` method.
3. The storage layer stops its background snapshot thread, writes a final snapshot and closes the WAL.

Without this handler, the server runs as PID 1 in the container, which ignores SIGTERM by default. Docker would then wait 10 seconds and force-kill the process with no final snapshot.

Result in our test: `docker stop kv` completed in **0.45 seconds**, and the last log line was `Snapshot saved: 301 keys`. The container exited with `Status=exited ExitCode=0 OOMKilled=false`.

### Docker Design Choices

- **Lightweight base image:** `python:3.11-alpine` keeps the image small (about 115 MB). The dependencies are pure Python, so no extra build tools are needed on Alpine.
- **Dependency layer caching:** `requirements.txt` is copied and installed before the source files, so a code change reuses the cached dependency layer and rebuilds in seconds.
- **Unbuffered output:** `PYTHONUNBUFFERED=1` makes log lines appear immediately in `docker logs`; `PYTHONDONTWRITEBYTECODE=1` avoids writing `.pyc` files.
- **Network accessibility:** The server starts with `--host 0.0.0.0` so it is reachable through the published port.
- **Exec-form `CMD`:** The JSON-array form runs Python directly as the main process, so it receives `docker stop`'s SIGTERM.
- **Persistent storage:** The named volume `kv-data` is mounted at `/app/data`, so snapshot and WAL files survive container recreation.
- **Small build context:** `.dockerignore` excludes Git metadata, virtual environments, Python caches, and local `data/` and `logs/` folders.

## API

Request and response bodies use JSON.

| Request | Success | Errors |
|---|---|---|
| `GET /` | `200` server status and key count | |
| `GET /<key>` | `200` with the stored key and value | `404` key not found, `400` key longer than 256 characters |
| `PUT /<key>` with body `{"value": <any JSON value>}` | `201` created, `200` updated | `400` body not JSON or missing `value`, `413` body larger than 1 MiB |
| `POST /<key>` | Same as PUT | Same as PUT |
| `DELETE /<key>` | `200` deleted | `404` key not found |

Unsupported methods return `405`, unknown URLs return `404`, and unexpected server errors return `500`. Every error is JSON of the form `{"error": ..., "message": ...}`.

### API Examples (macOS / Linux)

```bash
curl -X PUT http://127.0.0.1:8080/demo-key -H "Content-Type: application/json" -d '{"value":"hello"}'
curl http://127.0.0.1:8080/demo-key
curl -X DELETE http://127.0.0.1:8080/demo-key
```

### API Examples (Windows PowerShell)

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8080/demo-key" -Method Put -ContentType "application/json" -Body '{"value":"hello"}'
Invoke-RestMethod -Uri "http://127.0.0.1:8080/demo-key" -Method Get
Invoke-RestMethod -Uri "http://127.0.0.1:8080/demo-key" -Method Delete
```

## Testing

The project uses pytest. With the virtual environment activated, run from the project root:

```bash
python -m pytest -v
```

On Windows, the virtual environment's Python can also be used directly:

```powershell
.\.venv\Scripts\python.exe -m pytest -v
```

All **17 tests pass**. They cover:

- API endpoint functionality
- Error responses and request validation
- Storage operations
- Concurrent access to the same key
- Persistence across restarts
- WAL crash recovery
- Snapshot behavior
- Handling of malformed log entries

## Benchmarking

`benchmark.py` measures throughput and latency with concurrent requests. Start the server (locally or in Docker), then run:

```bash
python benchmark.py
```

The benchmark uses three concurrent worker threads. It performs 300 writes, then reads back the same 300 keys and checks that every value matches what was written.

### Local Server Results

| Metric | Run 1 | Run 2 |
|---|---:|---:|
| Successful SET operations | 300 | 300 |
| Successful GET operations | 300 | 300 |
| Errors | 0 | 0 |
| Value mismatches | 0 | 0 |
| Total successful operations | 600 | 600 |
| Total duration | 1.35 s | 1.31 s |
| Overall throughput | 445.9 ops/s | 457.1 ops/s |

### Docker Container Results (macOS, Docker Desktop)

| Phase | Successful | Errors | Mismatches | Throughput | Avg latency | p99 latency |
|---|---:|---:|---:|---:|---:|---:|
| SET | 300 | 0 | 0 | 137.5 ops/s | 21.73 ms | 110.51 ms |
| GET | 300 | 0 | 0 | 252.5 ops/s | 11.83 ms | 19.71 ms |
| **Total** | **600 in 3.37 s** | **0** | **0** | **178.1 ops/s** | | |

All requests succeeded in both environments. Throughput is lower in Docker because Docker Desktop on macOS runs containers inside a Linux virtual machine and forwards port 8080 through a network proxy, which adds latency to every request. The server's own processing time stayed below 1 ms for most requests, according to the `latency_ms` values in its log.

Results vary with system load, Docker configuration, storage performance and the number of concurrent clients.

## Logging and Persistence

### Request Logging

The server writes request logs to `logs/kvstore.log`, rotated at 10 MB with 5 old files kept. Each line includes:

- Timestamp
- HTTP method
- Requested key
- HTTP status code
- Client address
- Request latency

Logs are also printed to the console, which is what `docker logs kv` shows when running in Docker.

### Write-Ahead Logging

Every PUT and DELETE is appended to the write-ahead log and flushed before memory is changed or the client receives a response, so acknowledged writes survive a process crash.

The `--fsync` option forces each write to the physical disk for stronger durability. Without it, writes survive a process crash but may not survive a sudden power loss.

### Snapshots

Every 30 seconds by default, a background thread saves the whole store to `snapshot.json`. It writes to a temporary file and then renames it atomically, so a crash during the save never leaves a broken snapshot. After each snapshot, the application starts a new WAL file and removes older ones that are no longer needed.

### Startup Recovery

When the server starts, it:

1. Loads the most recent snapshot, if one exists.
2. Replays WAL entries written after that snapshot.
3. Rebuilds the in-memory key-value store.
4. Starts accepting requests.

### Docker Volume Persistence

In Docker, the data lives in the named volume `kv-data`, mounted at `/app/data`. This keeps persistent storage separate from the container's writable layer, so the data remains available when a container is stopped, removed and recreated with the same volume.

## Future Improvements

- Readers-writer or per-key locks to improve concurrency.
- Group commit to reduce the cost of frequent `fsync` calls.
- Compare-and-swap operations and key expiry (TTL).
- Authentication and TLS.
- Monitoring and operational metrics, plus a Docker `HEALTHCHECK` using the `GET /` endpoint.
- Running the container as a non-root user.
- Benchmarks with larger workloads and higher concurrency.
- Partitioning, replication and distributed storage.