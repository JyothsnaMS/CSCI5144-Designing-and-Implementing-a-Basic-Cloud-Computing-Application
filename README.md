# Single-Server Key-Value Store

## Overview

This project implements a basic single-server key-value store for the CSCI 5144 Cloud Computing assignment. It provides an HTTP API for storing, retrieving, updating, and deleting key-value pairs.

The project demonstrates core cloud computing concepts, including concurrent request handling, data persistence, error handling, logging, and performance benchmarking.

## Features

- **PUT:** Create a new key-value pair or update an existing value.
- **GET:** Retrieve the value associated with a key.
- **DELETE:** Remove a key-value pair.
- **Health check:** Check whether the server is running.
- **Concurrency:** Handle concurrent operations safely through synchronization in the storage layer.
- **Persistence:** Use a write-ahead log (WAL), snapshots, and recovery mechanisms to preserve and restore stored data.
- **Error handling:** Return appropriate HTTP responses for missing keys and invalid requests.
- **Logging:** Record timestamps, request methods, keys, HTTP status codes, client addresses, and request latency.
- **Benchmarking:** Measure request throughput and latency using concurrent workers.

## Technologies

- Python 3.11
- Flask
- pytest
- Requests
- JSON-based HTTP requests and responses

## Project Structure

```text
cloud-assignment/
├── server.py           # Flask HTTP server and API endpoints
├── store.py            # Key-value storage and persistence logic
├── benchmark.py        # HTTP performance benchmark
├── try_store.py        # Storage experimentation script
├── requirements.txt    # Python dependencies
├── tests/
│   ├── test_server.py  # API endpoint tests
│   └── test_store.py   # Storage, concurrency, and recovery tests
├── data/               # Storage data and persistence files
├── logs/               # Application logs
└── test-logs/           # Test-related logs
```

## Setup and Installation

The project was developed and tested using Python 3.11 on Windows.

Open PowerShell in the project directory and create a virtual environment if one does not already exist:

```powershell
python -m venv .venv
```

Install the required dependencies:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Running the Server

Start the Flask server using:

```powershell
.\.venv\Scripts\python.exe server.py
```

The server listens on port `8080` and is available locally at:

`http://127.0.0.1:8080`

Keep the server running while sending requests from another terminal.

## API Usage

The API uses JSON for request bodies and responses.

### Health Check

Send a GET request to `/` to check server availability.

### Create or Update a Key

Send a PUT request to `/<key>` with a JSON body containing a value.

Example using PowerShell:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8080/demo-key" -Method Put -ContentType "application/json" -Body '{"value":"hello"}'
```

### Retrieve a Value

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8080/demo-key" -Method Get
```

### Delete a Key

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8080/demo-key" -Method Delete
```

A request for a nonexistent key returns an appropriate not-found response. The exact response format depends on the operation.

## Testing

Run the automated tests from the project directory:

```powershell
.\.venv\Scripts\python.exe -m pytest -v
```

The verified test run completed with **17 passed**. The tests cover server endpoints, storage operations, concurrent access, restart persistence, crash recovery, malformed log handling, and snapshot behavior.

## Benchmarking

Start the server in one terminal. In a second terminal, run:

```powershell
.\.venv\Scripts\python.exe .\benchmark.py
```

In the recorded local benchmark, three concurrent worker threads performed 300 write requests and 300 GET requests. The benchmark completed 600 successful operations in approximately 0.69 seconds, with overall throughput of approximately 869.2 operations per second.

These measurements represent a local baseline under light testing conditions and are not a measure of maximum system capacity.

## Logging and Persistence

Application request logs are written to the `logs/` directory. The logs include timestamps, operation types, keys, status codes, client addresses, and request latency.

The storage layer uses a write-ahead log, snapshots, and recovery mechanisms. These features are tested through restart, crash-recovery, and snapshot-related test cases.

## Future Improvements

Potential improvements include testing larger workloads and higher concurrency levels, adding authentication and access controls, improving monitoring, and evaluating performance under sustained load or across multiple server instances.
