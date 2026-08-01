"""
Pytest configuration and shared fixtures.
"""

import pytest
from fastapi.testclient import TestClient

from src.storage import Storage, override_storage
from src.main import app


@pytest.fixture()
def mem_storage():
    """A fresh in-memory (no file) Storage instance per test."""
    return Storage(filepath=None)


@pytest.fixture()
def client(mem_storage):
    """TestClient wired to the in-memory storage override."""
    with override_storage(mem_storage):
        yield TestClient(app)


@pytest.fixture()
def seeded_client(client, mem_storage):
    """Client pre-loaded with a handful of known expenses."""
    expenses = [
        {"title": "Coffee", "amount": 4.50, "category": "Food", "date": "2024-07-10"},
        {"title": "Burger", "amount": 12.00, "category": "Food", "date": "2024-07-11"},
        {"title": "Bus pass", "amount": 30.00, "category": "Transport", "date": "2024-07-01"},
        {"title": "Netflix", "amount": 15.99, "category": "Entertainment", "date": "2024-06-15"},
        {"title": "Gym membership", "amount": 45.00, "category": "Health", "date": "2024-06-01"},
    ]
    ids = []
    for e in expenses:
        resp = client.post("/expenses/", json=e)
        assert resp.status_code == 201
        ids.append(resp.json()["id"])
    return client, ids
