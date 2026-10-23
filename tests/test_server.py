
import pytest

from server import create_app



class FakeStore:
    """Temporary in-memory store for testing the HTTP API."""

    def __init__(self):
        self.data = {}

    def get(self, key):
        if key in self.data:
            return True, self.data[key]
        return False, None

    def put(self, key, value):
        existed = key in self.data
        self.data[key] = value
        return existed

    def delete(self, key):
        if key not in self.data:
            return False
        del self.data[key]
        return True

    def __len__(self):
        return len(self.data)

@pytest.fixture
def client(tmp_path):
    store = FakeStore()
    app = create_app(store=store, log_dir=str(tmp_path / "logs"))
    app.config["TESTING"] = True

    with app.test_client() as test_client:
        yield test_client


def test_health_check(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.get_json()["status"] == "running"


def test_put_creates_key(client):
    response = client.put("/colour", json={"value": "blue"})
    assert response.status_code == 201
    assert response.get_json()["value"] == "blue"


def test_get_existing_key(client):
    client.put("/colour", json={"value": "blue"})
    response = client.get("/colour")
    assert response.status_code == 200
    assert response.get_json()["value"] == "blue"


def test_put_updates_key(client):
    client.put("/colour", json={"value": "blue"})
    response = client.put("/colour", json={"value": "green"})
    assert response.status_code == 200
    assert response.get_json()["value"] == "green"


def test_get_missing_key(client):
    response = client.get("/missing")
    assert response.status_code == 404


def test_delete_existing_key(client):
    client.put("/colour", json={"value": "blue"})
    response = client.delete("/colour")
    assert response.status_code == 200
    assert response.get_json()["deleted"] is True


def test_delete_missing_key(client):
    response = client.delete("/missing")
    assert response.status_code == 404


def test_put_requires_value(client):
    response = client.put("/colour", json={"other": "blue"})
    assert response.status_code == 400
