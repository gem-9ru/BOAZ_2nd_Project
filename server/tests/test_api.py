import pathlib

from fastapi.testclient import TestClient

from server.app import app


def test_health():
    assert TestClient(app).get("/health").json() == {"ok": True}


def test_engine_has_no_streamlit():
    src = "".join(p.read_text(encoding="utf-8") for p in pathlib.Path(__file__).resolve().parents[1].joinpath("engine").glob("*.py"))
    assert "streamlit" not in src
