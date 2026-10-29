# Single-Server Key-Value Store

## Overview

This project implements a single-server key-value store for the CSCI 5144 Cloud Computing assignment. It exposes an HTTP API for storing, retrieving, updating, and deleting key-value pairs.

It demonstrates core cloud computing concepts including concurrent request handling, data persistence, error handling, logging, performance benchmarking, and containerization using Docker.

## Features

- **PUT / POST:** Create a new key-value pair or update an existing one.
- **GET:** Retrieve the value stored under a key.
- **DELETE:** Remove a key and its value.
- **Health check:** `GET /` reports that the server is running and how many keys it holds.
- **Concurrency:** Storage operations are synchronized with a lock to protect shared data.
- **Persistence:** A write-ahead log (WAL), periodic snapshots, and startup recovery support data persistence across restarts.
- **Error handling:** Errors are returned as JSON with appropriate HTTP status codes.
- **Logging:** Requests are logged with timestamps, methods, keys, status codes, client addresses, and latency.
- **Benchmarking:** Throughput and latency are measured using concurrent client threads.
- **Docker support:** The application can be built and run inside a Docker container.
- **Persistent Docker storage:** A named Docker volume preserves application data across container recreation.
- **Graceful shutdown:** SIGTERM handling allows the server to close its storage layer when the container is stopped normally.

## Technologies

- Python 3.11
- Flask (HTTP routing)
- Waitress (multi-threaded WSGI server)
- pytest (automated tests)
- Requests (benchmark client)
- Docker
- Alpine Linux
- JSON request and response bodies

## Project Structure

```text
cloud-assignment/
├── server.py             # HTTP server, API endpoints, logging, signal handling
├── store.py              # Storage, locking, WAL, snapshots, recovery
├── benchmark.py          # Concurrent performance benchmark
├── try_store.py          # Script for testing the storage layer directly
├── requirements.txt      # Python dependencies
├── Dockerfile            # Docker image build instructions
├── .dockerignore         # Files excluded from the Docker build context
├── README.md             # Project documentation
├── tests/
│   ├── test_server.py    # API endpoint tests
│   └── test_store.py     # Storage, concurrency, and recovery tests
├── data/                 # Runtime snapshot and WAL files
└── logs/                 # Runtime request logs
```

The `data/` and `logs/` directories are created at runtime and are not committed to the repository.

## Setup and Installation

Python 3.9 or newer is required. The project was developed and tested using Python 3.11.

### macOS / Linux

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Windows (PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

If PowerShell prevents virtual environment activation, the environment's Python executable can be used directly:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Running the Server Locally

With the virtual environment activated:

```bash
python server.py
```

The server listens on:

```text
http://127.0.0.1:8080
```

Keep the server running and send requests from a second terminal.

Press **Ctrl+C** to stop the server gracefully. The storage layer closes and saves a final snapshot.

### Server Options

| Option | Default | Description |
|---|---|---|
| `--host` | `127.0.0.1` | Address to listen on |
| `--port` | `8080` | Server port |
| `--threads` | `8` | Number of worker threads |
| `--data-dir` | `data` | Directory containing snapshots and WAL files |
| `--log-dir` | `logs` | Directory containing request logs |
| `--snapshot-interval` | `30` | Seconds between background snapshots |
| `--fsync` | Disabled | Force WAL writes to disk for stronger durability |

Example:

```bash
python server.py --port 9000 --fsync
```

## Running with Docker

Docker provides a consistent environment for running the key-value store without manually installing Python dependencies on the host machine.

### Prerequisites

- Docker Desktop installed and running.
- Project source code available locally.
- Port 8080 available on the host machine.

### 1. Build the Docker Image

Open a terminal in the project root directory and run:

```bash
docker build -t kv-store .
```

This builds a Docker image named `kv-store` using the project's `Dockerfile`.

The Dockerfile uses Python 3.11 on Alpine Linux, installs the dependencies from `requirements.txt`, and copies the application files into the image.

### 2. Run the Docker Container

```bash
docker run -d --name kv -p 8080:8080 -v kv-data:/app/data kv-store
```

Explanation of the command:

| Option | Purpose |
|---|---|
| `-d` | Runs the container in detached mode (background) |
| `--name kv` | Assigns the container the name `kv` |
| `-p 8080:8080` | Maps host port 8080 to container port 8080 |
| `-v kv-data:/app/data` | Mounts a named Docker volume for persistent data |
| `kv-store` | Specifies the image to run |

The application is accessible at:

```text
http://localhost:8080
```

The server binds to `0.0.0.0` inside the container so it can accept connections through Docker's port mapping.

### 3. Test the API

Create a key:

**macOS / Linux:**

```bash
curl -X PUT http://localhost:8080/docker-test \
  -H "Content-Type: application/json" \
  -d '{"value":"hello from Docker"}'
```

Retrieve the key:

```bash
curl http://localhost:8080/docker-test
```

Delete the key:

```bash
curl -X DELETE http://localhost:8080/docker-test
```

**Windows PowerShell:**

Create a key:

```powershell
Invoke-RestMethod -Method Put -Uri "http://localhost:8080/docker-test" -ContentType "application/json" -Body '{"value":"hello from Docker"}'
```

Retrieve the key:

```powershell
Invoke-RestMethod -Method Get -Uri "http://localhost:8080/docker-test"
```

Delete the key:

```powershell
Invoke-RestMethod -Method Delete -Uri "http://localhost:8080/docker-test"
```

### 4. View Container Logs

```bash
docker logs kv
```

To follow logs continuously:

```bash
docker logs -f kv
```

### 5. Stop and Restart the Container

Stop the container gracefully:

```bash
docker stop kv
```

Restart the existing container:

```bash
docker start kv
```

Remove the stopped container:

```bash
docker rm kv
```

To recreate it using the same persistent volume:

```bash
docker run -d --name kv -p 8080:8080 -v kv-data:/app/data kv-store
```

The named volume is retained even after the container is removed.

### 6. Verify Persistent Storage

Create a key:

```powershell
Invoke-RestMethod -Method Put -Uri "http://localhost:8080/persist-test" -ContentType "application/json" -Body '{"value":"saved-data"}'
```

Stop and remove the container:

```bash
docker stop kv
docker rm kv
```

Recreate it using the same volume:

```bash
docker run -d --name kv -p 8080:8080 -v kv-data:/app/data kv-store
```

Retrieve the stored key:

```powershell
Invoke-RestMethod -Method Get -Uri "http://localhost:8080/persist-test"
```

The value should still be available because the application's data is stored in the named Docker volume rather than the container's writable layer.

### 7. Test Crash Recovery

Create a key:

```powershell
Invoke-RestMethod -Method Put -Uri "http://localhost:8080/crash-test" -ContentType "application/json" -Body '{"value":"recover-me"}'
```

Forcefully terminate the container:

```bash
docker kill kv
```

Remove the container:

```bash
docker rm kv
```

Recreate the container with the existing volume:

```bash
docker run -d --name kv -p 8080:8080 -v kv-data:/app/data kv-store
```

Retrieve the key:

```powershell
Invoke-RestMethod -Method Get -Uri "http://localhost:8080/crash-test"
```

In our local test, the value `recover-me` was successfully recovered after recreating the container.

This demonstrates WAL-based recovery for the tested container termination scenario. It does not guarantee recovery from every possible storage failure or sudden power loss.

### 8. Graceful Shutdown

The server handles the SIGTERM signal sent by Docker during a normal container stop.

When `docker stop kv` is executed:

1. Docker sends SIGTERM to the container's main process.
2. The Python signal handler raises `KeyboardInterrupt`.
3. The server's cleanup logic calls the storage layer's `close()` method.
4. The storage layer stops its background snapshot thread, writes a final snapshot, and closes the WAL.

The clean-shutdown test returned:

```text
Status=exited ExitCode=0 OOMKilled=false
```

This confirms that the tested container stopped successfully without being killed due to an out-of-memory condition.

### Docker Design Choices

**Lightweight base image**

The Dockerfile uses `python:3.11-alpine` to reduce the image size compared with larger general-purpose Python images.

**Dependency layer caching**

The Dockerfile copies `requirements.txt` and installs dependencies before copying the application source files. This allows Docker to reuse the dependency layer when only application code changes.

**Unbuffered Python output**

`PYTHONUNBUFFERED=1` allows application output to appear promptly in Docker logs.

**Network accessibility**

The container starts the server with `--host 0.0.0.0`, making it accessible through Docker's published port.

**Exec-form CMD**

The Dockerfile uses the JSON-array form of `CMD`, allowing the Python process to receive termination signals directly.

**Persistent storage**

The named volume `kv-data` is mounted at `/app/data`, preserving the application's snapshot and WAL files across container recreation.

**Build context exclusions**

The `.dockerignore` file excludes Git metadata, virtual environments, Python caches, local data, and log files from the Docker build context.

## API

Request and response bodies use JSON.

| Request | Success | Errors |
|---|---|---|
| `GET /` | `200` server status and key count | |
| `GET /<key>` | `200` with stored key and value | `404` key not found, `400` invalid key |
| `PUT /<key>` | `201` created, `200` updated | `400` invalid JSON or missing value, `413` oversized request |
| `POST /<key>` | `201` created, `200` updated | `400` invalid JSON or missing value, `413` oversized request |
| `DELETE /<key>` | `200` deleted | `404` key not found |

Unsupported methods return `405`, unknown URLs return `404`, and unexpected server errors return `500`.

Errors use JSON responses containing an error type and message.

### API Examples (macOS / Linux)

Create or update a key:

```bash
curl -X PUT http://127.0.0.1:8080/demo-key \
  -H "Content-Type: application/json" \
  -d '{"value":"hello"}'
```

Retrieve the key:

```bash
curl http://127.0.0.1:8080/demo-key
```

Delete the key:

```bash
curl -X DELETE http://127.0.0.1:8080/demo-key
```

### API Examples (Windows PowerShell)

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8080/demo-key" -Method Put -ContentType "application/json" -Body '{"value":"hello"}'

Invoke-RestMethod -Uri "http://127.0.0.1:8080/demo-key" -Method Get

Invoke-RestMethod -Uri "http://127.0.0.1:8080/demo-key" -Method Delete
```

## Testing

The project uses pytest for automated testing.

From the project directory, run:

```bash
python -m pytest -v
```

On Windows, the virtual environment's Python executable can also be used:

```powershell
.\.venv\Scripts\python.exe -m pytest -v
```

All **17 tests passed** in the local test run.

The test suite covers:

- API endpoint functionality
- Error responses and request validation
- Storage operations
- Concurrent access
- Persistence across restarts
- WAL recovery
- Snapshot behavior
- Handling malformed log entries

## Benchmarking

The project includes `benchmark.py` for measuring throughput and latency under concurrent requests.

Start the server, then run:

```bash
python benchmark.py
```

The current benchmark uses three concurrent worker threads and performs 300 writes followed by 300 reads.

It verifies that retrieved values match the values previously stored.

### Local Benchmark Results

| Metric | Run 1 | Run 2 |
|---|---:|---:|
| Successful SET operations | 300 | 300 |
| Successful GET operations | 300 | 300 |
| Errors | 0 | 0 |
| Value mismatches | 0 | 0 |
| Total successful operations | 600 | 600 |
| Total duration | 1.35 s | 1.31 s |
| Overall throughput | 445.9 ops/s | 457.1 ops/s |

These results demonstrate successful concurrent requests under the tested workload.

Performance may vary depending on system load, Docker configuration, storage performance, and the number of concurrent clients.

## Logging and Persistence

### Request Logging

The server logs requests to:

```text
logs/kvstore.log
```

The logs include request information such as:

- Timestamp
- HTTP method
- Requested key
- HTTP status code
- Client address
- Request latency

Log files are rotated when they reach the configured size.

Logs are also printed to the console and can be viewed through Docker using:

```bash
docker logs kv
```

### Write-Ahead Logging

The application uses a write-ahead log to record PUT and DELETE operations.

Each operation is appended to the WAL and flushed before the operation completes.

The `--fsync` option can be enabled for stronger durability guarantees by requesting that writes be synchronized to disk.

Without per-write `fsync`, WAL recovery can work after a process crash, but acknowledged writes are not guaranteed to survive sudden power loss or every underlying storage failure.

### Snapshots

By default, the application creates a snapshot every 30 seconds.

Snapshots capture the current key-value store and are written using a temporary file followed by an atomic rename.

After creating a snapshot, the application rotates the WAL and removes older log files that are no longer needed.

### Startup Recovery

When the server starts:

1. It loads the most recent snapshot, if available.
2. It replays subsequent WAL entries.
3. It reconstructs the in-memory key-value store.
4. It begins accepting requests.

This mechanism supports recovery after normal restarts and certain crash scenarios.

### Docker Volume Persistence

When running with Docker, application data is stored in the named volume:

```text
kv-data
```

Mounted at:

```text
/app/data
```

This separates persistent storage from the container's writable layer.

The data remains available when a container is stopped, removed, and recreated using the same volume.

## Future Improvements

- Implement readers-writer or per-key locks to improve concurrency.
- Introduce group commit to reduce the cost of frequent `fsync` operations.
- Add compare-and-swap operations.
- Support key expiration using TTL.
- Add authentication and TLS.
- Improve monitoring and operational metrics.
- Extend benchmarks to larger workloads and higher concurrency.
- Explore partitioning, replication, and distributed storage.
