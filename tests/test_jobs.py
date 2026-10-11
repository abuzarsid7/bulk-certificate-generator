def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_routers_mounted(client):
    paths = client.get("/openapi.json").json()["paths"]
    assert "/health" in paths


def test_unknown_job_route_is_404(client):
    assert client.get("/api/v1/jobs/does-not-exist").status_code == 404
