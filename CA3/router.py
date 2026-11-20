
import argparse
import os
import threading

import requests
from flask import Flask, Response, jsonify, request
from waitress import serve

from hash_ring import ConsistentHashRing


_thread_local = threading.local()


def get_session():
    if not hasattr(_thread_local, "session"):
        _thread_local.session = requests.Session()
    return _thread_local.session


def create_app(store_urls=None, replicas=100):
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 1024 * 1024

    if store_urls is None:
        store_urls = os.environ.get("STORE_URLS", "").split(",")

    store_urls = [
        url.strip().rstrip("/")
        for url in store_urls
        if url.strip()
    ]

    if not store_urls:
        raise ValueError("No store URLs configured.")

    ring = ConsistentHashRing(replicas=replicas)

    for url in store_urls:
        ring.add_node(url)

    app.extensions["hash_ring"] = ring

    @app.route("/", methods=["GET"])
    def health():
        return jsonify({
            "status": "running",
            "service": "router",
            "stores": ring.get_nodes()
        }), 200

    @app.route("/<key>", methods=["GET", "PUT", "POST", "DELETE"])
    def route_key(key):
        store_url = ring.get_node(key)
        target_url = f"{store_url}/{key}"

        headers = {}

        if request.content_type:
            headers["Content-Type"] = request.content_type

        try:
            backend_response = get_session().request(
                method=request.method,
                url=target_url,
                data=request.get_data(),
                headers=headers,
                timeout=10
            )

            return Response(
                backend_response.content,
                status=backend_response.status_code,
                content_type=backend_response.headers.get(
                    "Content-Type", "application/json"
                )
            )

        except requests.RequestException:
            return jsonify({
                "error": "Service Unavailable",
                "message": "The selected store is unreachable."
            }), 503

    return app


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--threads", type=int, default=8)
    parser.add_argument("--replicas", type=int, default=100)

    args = parser.parse_args()

    app = create_app(replicas=args.replicas)

    serve(
        app,
        host=args.host,
        port=args.port,
        threads=args.threads
    )


if __name__ == "__main__":
    main()

