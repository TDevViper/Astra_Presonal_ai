"""Tests for API authentication."""
import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture
def app():
    from flask import Flask, jsonify
    from api.auth import require_api_key
    app = Flask(__name__)
    app.config["TESTING"] = True

    @app.route("/test", methods=["GET", "POST"])
    @require_api_key
    def protected():
        return jsonify({"ok": True})

    return app


@pytest.fixture
def client(app):
    return app.test_client()


def test_no_key_configured_returns_500(client, monkeypatch):
    monkeypatch.delenv("ASTRA_API_KEY", raising=False)
    resp = client.get("/test")
    assert resp.status_code == 500
    assert b"not configured" in resp.data


def test_correct_key_in_header_returns_200(client, monkeypatch):
    monkeypatch.setenv("ASTRA_API_KEY", "testkey123")
    resp = client.get("/test", headers={"X-API-Key": "testkey123"})
    assert resp.status_code == 200


def test_wrong_key_returns_401(client, monkeypatch):
    monkeypatch.setenv("ASTRA_API_KEY", "testkey123")
    resp = client.get("/test", headers={"X-API-Key": "wrongkey"})
    assert resp.status_code == 401


def test_missing_key_header_returns_401(client, monkeypatch):
    monkeypatch.setenv("ASTRA_API_KEY", "testkey123")
    resp = client.get("/test")
    assert resp.status_code == 401


def test_key_in_query_param_rejected(client, monkeypatch):
    monkeypatch.setenv("ASTRA_API_KEY", "testkey123")
    resp = client.get("/test?api_key=testkey123")
    assert resp.status_code == 401


def test_key_in_body_rejected(client, monkeypatch):
    monkeypatch.setenv("ASTRA_API_KEY", "testkey123")
    resp = client.post("/test", json={"api_key": "testkey123"})
    assert resp.status_code == 401


def test_empty_string_key_rejected(client, monkeypatch):
    monkeypatch.setenv("ASTRA_API_KEY", "testkey123")
    resp = client.get("/test", headers={"X-API-Key": ""})
    assert resp.status_code == 401
