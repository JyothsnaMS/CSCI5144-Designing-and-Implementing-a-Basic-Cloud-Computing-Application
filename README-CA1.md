# Single-Server Key-Value Store

## Overview

This project implements a single-server key-value store for the CSCI 5144 Cloud Computing assignment. It exposes an HTTP API for storing, retrieving, updating and deleting key-value pairs.

It demonstrates core cloud computing concepts: concurrent request handling, data persistence, error handling, logging and performance benchmarking.

## Features

- **PUT / POST:** Create a new key-value pair or update an existing one.
- **GET:** Retrieve the value stored under a key.
- **DELETE:** Remove a key and its value.
- **Health check:** `GET /` reports that the server is running and how many keys it holds.
- **Concurrency:** All storage operations are synchronized with a lock, so concurrent PUT/DELETE requests on the same key are safe.
- **Persistence:** A write-ahead log (WAL), periodic snapshots and startup recovery preserve data across restarts and crashes.
- **Error handling:** Every error is returned as JSON with an appropriate HTTP status code.
- **Logging:** Every request is logged with a timestamp, method, key, status code, client address and latency.
- **Benchmarking:** Throughput and latency are measured with concurrent client threads.

## Technologies

- Python 3.11
- Flask (HTTP routing)
- Waitress (multi-threaded production WSGI server)
- pytest (automated tests)
- Requests (benchmark client)
- JSON request and response bodies

## Project Structure

```text
CSCI5144-Designing-and-Implementing-a-Basic-Cloud-Computing-Application/
├── server.py            # HTTP server: API endpoints, validation, errors, logging
├── store.py             # Key-value storage: locking, write-ahead log, snapshots, 
├── benchmark.py         # Corrected benchmark that reads back the keys it writes
├── try_store.py         # Small script for trying the storage layer directly
├── requirements.txt     # Python dependencies
├── tests/
│   ├── test_server.py   # API endpoint tests
│   └── test_store.py    # Storage, concurrency and recovery tests
├── data/                # Snapshot and log files (created at runtime, not committed)
└── logs/                # Request logs (created at runtime, not committed)
```

## Setup and Installation

Python 3.9 or newer is required. The project was developed and tested with Python 3.11 on Windows and macOS.

**macOS / Linux:**

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**Windows (PowerShell):**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Running the Server

With the virtual environment activated:

```bash
python server.py
```

The server listens on `http://127.0.0.1:8080`. Keep it running and send requests from a second terminal. Stop it with **Ctrl+C**; it saves a final snapshot before exiting.

### Options

| Option | Default | Description |
| --- | --- | --- |
| `--host` | `127.0.0.1` | Address to listen on (`0.0.0.0` accepts remote clients) |
| `--port` | `8080` | Port to listen on |
| `--threads` | `8` | Number of worker threads |
| `--data-dir` | `data` | Folder for the snapshot and write-ahead log |
| `--log-dir` | `logs` | Folder for `kvstore.log` |
| `--snapshot-interval` | `30` | Seconds between snapshots (`0` disables background snapshots) |
| `--fsync` | off | Force every write to disk (survives power loss; slower) |

Example: `python server.py --port 9000 --fsync`

## API

Request and response bodies are JSON.

| Request | Success | Errors |
| --- | --- | --- |
| `GET /` | `200` server status and key count | |
| `GET /<key>` | `200` `{"key": ..., "value": ...}` | `404` key not found, `400` key longer than 256 characters |
| `PUT /<key>` or `POST /<key>` with body `{"value": <any JSON value>}` | `201` created, `200` updated | `400` body is not JSON or has no `value`, `413` body larger than 1 MiB |
| `DELETE /<key>` | `200` `{"key": ..., "deleted": true}` | `404` key not found |

Unsupported methods return `405`, unknown URLs `404`, and unexpected server errors `500`, all as JSON of the form `{"error": ..., "message": ...}`.

### Examples (macOS / Linux, curl)

```bash
curl -X PUT http://127.0.0.1:8080/demo-key -H "Content-Type: application/json" -d '{"value": "hello"}'
curl http://127.0.0.1:8080/demo-key
curl -X DELETE http://127.0.0.1:8080/demo-key
curl http://127.0.0.1:8080/demo-key          # 404: key no longer exists
```

### Examples (Windows PowerShell)

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8080/demo-key" -Method Put -ContentType "application/json" -Body '{"value":"hello"}'
Invoke-RestMethod -Uri "http://127.0.0.1:8080/demo-key" -Method Get
Invoke-RestMethod -Uri "http://127.0.0.1:8080/demo-key" -Method Delete
```

## Testing

Stop the server, then run from the project folder:

```bash
python -m pytest -v
```

All **17 tests pass**. They cover the API endpoints, error responses, storage operations, concurrent access to the same key, restart persistence, crash recovery, malformed log lines and snapshot behavior.

## Benchmarking

Start the server in one terminal, then run in a second terminal:

```bash
python benchmark.py          # benchmark provided with the assignment
```

**Note on `benchmark.py`:** it stores `key_0, key_2, key_4, ...` but reads `key_1, key_3, key_5, ...`, keys that are never stored. The server correctly answers those reads with `404 Not Found`, so the benchmark prints 150 "Error during get" lines. This is the required error handling working, not a failure. The benchmark also counts 600 operations while sending only 300, so its reported throughput is doubled.

`benchmark_fixed.py` reads back the keys it writes. In our local run with three concurrent worker threads, 300 writes and 300 reads completed with no errors in about 0.69 seconds (about 869 operations per second). Writes averaged 3.77 ms (p99 8.33 ms) and reads 3.11 ms (p99 5.28 ms). These numbers are a local baseline under light load, not the system's maximum capacity.

## Logging and Persistence

**Logging.** Every request is written to `logs/kvstore.log` (rotated at 10 MB, 5 files kept) and printed to the console, for example:

```text
2026-10-22 23:59:23,594 INFO operation=PUT key='a' status=201 client=127.0.0.1 latency_ms=0.54
```

**Persistence.** Each PUT or DELETE is appended to a write-ahead log in `data/` and flushed before memory is changed or the client receives a response, so acknowledged writes survive a crash. Every 30 seconds a background thread saves the whole store to `data/snapshot.json` (written to a temporary file, then atomically renamed), starts a new log file and deletes older ones. On startup the server loads the snapshot and replays any newer log entries.

To see recovery in action:

1. Store a key: `curl -X PUT http://127.0.0.1:8080/survivor -H "Content-Type: application/json" -d '{"value": "still here"}'`
2. Crash the server: press **Ctrl+\\** in its terminal (macOS/Linux), or close the terminal window (Windows).
3. Start it again with `python server.py`.
4. `curl http://127.0.0.1:8080/survivor` still returns the value.

## Future Improvements

- A readers-writer or per-key lock, so reads and unrelated writes run in parallel.
- Group commit, to make `--fsync` cheaper.
- Compare-and-swap and key expiry (TTL).
- Partitioning with consistent hashing and replication across multiple servers.
- Authentication, TLS and monitoring.
- Benchmarks with larger workloads, higher concurrency and sustained load.