# tests/test_routes.py
import pytest
from app.main import create_app
import app.db as db
import json

@pytest.fixture(autouse=True)
def env_setup(tmp_path, monkeypatch):
    dbfile = str(tmp_path / 'test_scans.db')
    monkeypatch.setenv('DB_PATH', dbfile)
    monkeypatch.setenv('USE_FIRESTORE', '0')
    monkeypatch.setenv('LLM_PROVIDER', 'local')
    db.init_db()

@pytest.fixture
def client(monkeypatch):
    class DummyResp:
        def __init__(self, text):
            self.text = text

    def fake_get(url, timeout, allow_redirects, headers):
        return DummyResp('<html><head><title>Example Title</title></head><body>OK</body></html>')

    import requests
    monkeypatch.setattr(requests, 'get', fake_get)

    app = create_app()
    app.config['TESTING'] = True
    return app.test_client()


def test_scan_and_list(client):
    r = client.post('/scan', json={'url': 'http://example.com'})
    assert r.status_code == 201

    data = r.get_json()
    assert data['title'] == 'Example Title'

    r2 = client.get('/scans')
    assert r2.status_code == 200

    arr = r2.get_json()
    assert isinstance(arr, list)
