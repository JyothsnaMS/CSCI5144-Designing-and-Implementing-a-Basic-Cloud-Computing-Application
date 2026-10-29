
import argparse
import logging
import os
import signal
import time
from logging.handlers import RotatingFileHandler

from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException

from store import KVStore


MAX_KEY_LENGTH = 256
MAX_BODY_SIZE = 1024 * 1024  # 1 MiB


def configure_logging(log_dir):
    os.makedirs(log_dir, exist_ok=True)

    logger = logging.getLogger("kvstore")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    if not logger.handlers:
        formatter = logging.Formatter(
            "%(asctime)s %(levelname)s %(message)s"
        )

        file_handler = RotatingFileHandler(
            os.path.join(log_dir, "kvstore.log"),
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)

        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    return logger


def create_app(store=None, log_dir="logs"):
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = MAX_BODY_SIZE

    logger = configure_logging(log_dir)
    app.extensions["kvstore"] = (
        store if store is not None else KVStore()
    )

    @app.before_request
    def start_timer():
        request.start_time = time.perf_counter()

    @app.after_request
    def log_request(response):
        started = getattr(
            request, "start_time", time.perf_counter()
        )
        elapsed_ms = (time.perf_counter() - started) * 1000

        key = (
            request.view_args.get("key", "-")
            if request.view_args
            else "-"
        )
        client_ip = request.remote_addr or "-"

        logger.info(
            "operation=%s key=%r status=%s client=%s latency_ms=%.2f",
            request.method,
            key,
            response.status_code,
            client_ip,
            elapsed_ms,
        )
        return response

    @app.errorhandler(HTTPException)
    def handle_http_error(error):
        return jsonify({
            "error": error.name,
            "message": error.description,
        }), error.code

    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        logger.exception("Unexpected server error")
        return jsonify({
            "error": "Internal Server Error",
            "message": "An unexpected error occurred.",
        }), 500

    @app.route("/", methods=["GET"])
    def health():
        return jsonify({
            "status": "running",
            "keys": len(app.extensions["kvstore"]),
        })

    @app.route("/<key>", methods=["GET", "PUT", "POST", "DELETE"])
    def key_operations(key):
        if not key or len(key) > MAX_KEY_LENGTH:
            return jsonify({
                "error": "Bad Request",
                "message": (
                    f"Key must be between 1 and "
                    f"{MAX_KEY_LENGTH} characters."
                ),
            }), 400

        kv = app.extensions["kvstore"]

        if request.method == "GET":
            found, value = kv.get(key)

            if not found:
                return jsonify({
                    "error": "Not Found",
                    "message": f"Key '{key}' does not exist.",
                }), 404

            return jsonify({"key": key, "value": value}), 200

        if request.method in ("PUT", "POST"):
            if not request.is_json:
                return jsonify({
                    "error": "Bad Request",
                    "message": "Content-Type must be application/json.",
                }), 400

            body = request.get_json(silent=True)

            if not isinstance(body, dict) or "value" not in body:
                return jsonify({
                    "error": "Bad Request",
                    "message": (
                        "Request body must be a JSON object "
                        "containing 'value'."
                    ),
                }), 400

            try:
                updated = kv.put(key, body["value"])
            except OSError:
                logger.exception(
                    "Storage write failed for key %r", key
                )
                return jsonify({
                    "error": "Storage Error",
                    "message": "The value could not be saved.",
                }), 500

            return jsonify({
                "key": key,
                "value": body["value"],
                "operation": "updated" if updated else "created",
            }), 200 if updated else 201

        if request.method == "DELETE":
            deleted = kv.delete(key)

            if not deleted:
                return jsonify({
                    "error": "Not Found",
                    "message": f"Key '{key}' does not exist.",
                }), 404

            return jsonify({
                "key": key,
                "deleted": True,
            }), 200

    return app


def main():
    parser = argparse.ArgumentParser(
        description="Basic cloud key-value store"
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--threads", type=int, default=8)
    parser.add_argument("--data-dir", default="data")
    parser.add_argument("--log-dir", default="logs")
    parser.add_argument("--snapshot-interval", type=float, default=30.0)
    parser.add_argument("--fsync", action="store_true")
    args = parser.parse_args()

    store = KVStore(
        data_dir=args.data_dir,
        snapshot_interval=args.snapshot_interval,
        fsync=args.fsync,
    )

    app = create_app(store=store, log_dir=args.log_dir)

    from waitress import serve

    # Handle Docker's SIGTERM signal using the existing cleanup path.
    def handle_sigterm(signum, frame):
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, handle_sigterm)

    try:
        serve(
            app,
            host=args.host,
            port=args.port,
            threads=args.threads,
        )
    except KeyboardInterrupt:
        pass
    finally:
        store.close()


if __name__ == "__main__":
    main()
