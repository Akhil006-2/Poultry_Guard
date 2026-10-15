from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health():
    r=client.get('/health')
    assert r.status_code == 200
    assert r.json()['status'] == 'ok'

def test_status():
    r=client.get('/api/v1/status')
    assert r.status_code == 200
    assert 'database' in r.json()

def test_health_event_triage():
    r=client.post('/api/v1/health-events', json={'signs':['lethargy'],'sick_count':3,'deaths':0})
    assert r.status_code == 201
    assert r.json()['risk_level'] == 'watch'
