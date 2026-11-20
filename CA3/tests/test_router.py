
import requests

from router import create_app


class FakeResponse:
    def __init__(self, content, status_code, headers=None):
        self.content = content
        self.status_code = status_code
        self.headers = headers or {
            "Content-Type": "application/json"
        }


class FakeSession:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.calls = []

    def request(self, **kwargs):
        self.calls.append(kwargs)

        if self.error:
            raise self.error

        return self.response


def test_router_health():
    app = create_app(["http://store1:8080", "http://store2:8080"])
    client = app.test_client()

    response = client.get("/")

    assert response.status_code == 200
    assert response.json["status"] == "running"
    assert len(response.json["stores"]) == 2


def test_router_requires_stores():
    try:
        create_app([])
        assert False
    except ValueError:
        assert True


def test_get_request_forwarding(monkeypatch):
    app = create_app(["http://store1:8080"])
    client = app.test_client()

    fake_session = FakeSession(
        FakeResponse(b'{"key":"name","value":"Alice"}', 200)
    )

    monkeypatch.setattr(
        "router.get_session",
        lambda: fake_session
    )

    response = client.get("/name")

    assert response.status_code == 200
    assert response.json == {"key": "name", "value": "Alice"}
    assert fake_session.calls[0]["method"] == "GET"
    assert fake_session.calls[0]["url"] == "http://store1:8080/name"


def test_put_request_forwarding(monkeypatch):
    app = create_app(["http://store1:8080"])
    client = app.test_client()

    fake_session = FakeSession(
        FakeResponse(
            b'{"key":"name","value":"Alice","operation":"created"}',
            201
        )
    )

    monkeypatch.setattr(
        "router.get_session",
        lambda: fake_session
    )

    response = client.put("/name", json={"value": "Alice"})

    assert response.status_code == 201
    assert response.json["value"] == "Alice"
    assert fake_session.calls[0]["method"] == "PUT"


def test_post_request_forwarding(monkeypatch):
    app = create_app(["http://store1:8080"])
    client = app.test_client()

    fake_session = FakeSession(
        FakeResponse(b'{"key":"name","value":"Bob"}', 200)
    )

    monkeypatch.setattr(
        "router.get_session",
        lambda: fake_session
    )

    response = client.post("/name", json={"value": "Bob"})

    assert response.status_code == 200
    assert fake_session.calls[0]["method"] == "POST"


def test_delete_request_forwarding(monkeypatch):
    app = create_app(["http://store1:8080"])
    client = app.test_client()

    fake_session = FakeSession(
        FakeResponse(b'{"key":"name","deleted":true}', 200)
    )

    monkeypatch.setattr(
        "router.get_session",
        lambda: fake_session
    )

    response = client.delete("/name")

    assert response.status_code == 200
    assert response.json["deleted"] is True
    assert fake_session.calls[0]["method"] == "DELETE"


def test_backend_unavailable(monkeypatch):
    app = create_app(["http://store1:8080"])
    client = app.test_client()

    fake_session = FakeSession(
        error=requests.ConnectionError("Connection failed")
    )

    monkeypatch.setattr(
        "router.get_session",
        lambda: fake_session
    )

    response = client.get("/name")

    assert response.status_code == 503
    assert response.json["error"] == "Service Unavailable"
