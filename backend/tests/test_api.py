from io import BytesIO

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_analysis_requires_supported_documents() -> None:
    response = client.post(
        "/api/v1/analyses",
        files=[
            ("before_files", ("before.txt", BytesIO(b"before"), "text/plain")),
            ("after_files", ("after.txt", BytesIO(b"after"), "text/plain")),
        ],
    )
    assert response.status_code == 415

