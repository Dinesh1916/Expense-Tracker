"""
Tests for the /expenses endpoints.

Coverage:
  - POST /expenses/          create, validation errors
  - GET  /expenses/          list all, filter by category
  - GET  /expenses/search    keyword search
  - GET  /expenses/totals    overall + per-category totals
  - GET  /expenses/monthly   monthly summary
  - GET  /expenses/{id}      get single, 404
  - DELETE /expenses/{id}    delete, 404
"""

import pytest


# ---------------------------------------------------------------------------
# POST /expenses/
# ---------------------------------------------------------------------------

class TestCreateExpense:
    def test_creates_and_returns_expense(self, client):
        payload = {"title": "Coffee", "amount": 4.50, "category": "Food", "date": "2024-07-10"}
        resp = client.post("/expenses/", json=payload)
        assert resp.status_code == 201
        body = resp.json()
        assert body["title"] == "Coffee"
        assert body["amount"] == 4.50
        assert body["category"] == "Food"
        assert body["date"] == "2024-07-10"
        assert "id" in body and len(body["id"]) > 0

    def test_strips_whitespace_from_title_and_category(self, client):
        payload = {"title": "  Lunch  ", "amount": 10.0, "category": "  Food  ", "date": "2024-07-10"}
        resp = client.post("/expenses/", json=payload)
        assert resp.status_code == 201
        body = resp.json()
        assert body["title"] == "Lunch"
        assert body["category"] == "Food"

    def test_rounds_amount_to_two_decimal_places(self, client):
        payload = {"title": "Tip", "amount": 1.999, "category": "Food", "date": "2024-07-10"}
        resp = client.post("/expenses/", json=payload)
        assert resp.status_code == 201
        assert resp.json()["amount"] == 2.0

    def test_rejects_zero_amount(self, client):
        payload = {"title": "Free item", "amount": 0, "category": "Food", "date": "2024-07-10"}
        resp = client.post("/expenses/", json=payload)
        assert resp.status_code == 422

    def test_rejects_negative_amount(self, client):
        payload = {"title": "Refund", "amount": -5.0, "category": "Food", "date": "2024-07-10"}
        resp = client.post("/expenses/", json=payload)
        assert resp.status_code == 422

    def test_rejects_empty_title(self, client):
        payload = {"title": "", "amount": 5.0, "category": "Food", "date": "2024-07-10"}
        resp = client.post("/expenses/", json=payload)
        assert resp.status_code == 422

    def test_rejects_missing_fields(self, client):
        resp = client.post("/expenses/", json={"title": "No amount"})
        assert resp.status_code == 422

    def test_rejects_invalid_date(self, client):
        payload = {"title": "Item", "amount": 5.0, "category": "Food", "date": "not-a-date"}
        resp = client.post("/expenses/", json=payload)
        assert resp.status_code == 422

    def test_each_expense_gets_unique_id(self, client):
        payload = {"title": "Item", "amount": 1.0, "category": "Misc", "date": "2024-01-01"}
        id1 = client.post("/expenses/", json=payload).json()["id"]
        id2 = client.post("/expenses/", json=payload).json()["id"]
        assert id1 != id2


# ---------------------------------------------------------------------------
# GET /expenses/
# ---------------------------------------------------------------------------

class TestListExpenses:
    def test_empty_list_on_fresh_store(self, client):
        resp = client.get("/expenses/")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_returns_all_expenses(self, seeded_client):
        client, _ = seeded_client
        resp = client.get("/expenses/")
        assert resp.status_code == 200
        assert len(resp.json()) == 5

    def test_filter_by_category(self, seeded_client):
        client, _ = seeded_client
        resp = client.get("/expenses/?category=Food")
        assert resp.status_code == 200
        items = resp.json()
        assert len(items) == 2
        assert all(i["category"] == "Food" for i in items)

    def test_filter_category_case_insensitive(self, seeded_client):
        client, _ = seeded_client
        resp = client.get("/expenses/?category=food")
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_filter_nonexistent_category_returns_empty(self, seeded_client):
        client, _ = seeded_client
        resp = client.get("/expenses/?category=Nonexistent")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_results_sorted_most_recent_first(self, seeded_client):
        client, _ = seeded_client
        resp = client.get("/expenses/")
        dates = [item["date"] for item in resp.json()]
        assert dates == sorted(dates, reverse=True)


# ---------------------------------------------------------------------------
# GET /expenses/search
# ---------------------------------------------------------------------------

class TestSearchExpenses:
    def test_search_by_title_keyword(self, seeded_client):
        client, _ = seeded_client
        resp = client.get("/expenses/search?q=coffee")
        assert resp.status_code == 200
        body = resp.json()
        assert body["count"] == 1
        assert body["results"][0]["title"] == "Coffee"

    def test_search_by_category_keyword(self, seeded_client):
        client, _ = seeded_client
        resp = client.get("/expenses/search?q=transport")
        assert resp.status_code == 200
        assert resp.json()["count"] == 1

    def test_search_case_insensitive(self, seeded_client):
        client, _ = seeded_client
        resp = client.get("/expenses/search?q=NETFLIX")
        assert resp.status_code == 200
        assert resp.json()["count"] == 1

    def test_search_no_results(self, seeded_client):
        client, _ = seeded_client
        resp = client.get("/expenses/search?q=zzznomatch")
        assert resp.status_code == 200
        assert resp.json()["count"] == 0

    def test_search_missing_query_param_returns_422(self, client):
        resp = client.get("/expenses/search")
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET /expenses/totals
# ---------------------------------------------------------------------------

class TestTotals:
    def test_totals_empty_store(self, client):
        resp = client.get("/expenses/totals")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 0.0
        assert body["by_category"] == {}

    def test_totals_accuracy(self, seeded_client):
        client, _ = seeded_client
        resp = client.get("/expenses/totals")
        assert resp.status_code == 200
        body = resp.json()
        # 4.50 + 12.00 + 30.00 + 15.99 + 45.00 = 107.49
        assert body["total"] == pytest.approx(107.49)
        assert body["by_category"]["Food"] == pytest.approx(16.50)
        assert body["by_category"]["Transport"] == pytest.approx(30.00)
        assert body["by_category"]["Entertainment"] == pytest.approx(15.99)
        assert body["by_category"]["Health"] == pytest.approx(45.00)

    def test_totals_updates_after_delete(self, seeded_client):
        client, ids = seeded_client
        # Delete Coffee (4.50)
        del_resp = client.delete(f"/expenses/{ids[0]}")
        assert del_resp.status_code == 204
        resp = client.get("/expenses/totals")
        body = resp.json()
        assert body["total"] == pytest.approx(102.99)
        assert body["by_category"]["Food"] == pytest.approx(12.00)


# ---------------------------------------------------------------------------
# GET /expenses/monthly
# ---------------------------------------------------------------------------

class TestMonthlySummary:
    def test_monthly_empty_store(self, client):
        resp = client.get("/expenses/monthly")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_monthly_groups_by_month(self, seeded_client):
        client, _ = seeded_client
        resp = client.get("/expenses/monthly")
        assert resp.status_code == 200
        months = resp.json()
        # Seeded data spans July 2024 and June 2024
        assert len(months) == 2
        july = next(m for m in months if m["month"] == 7)
        june = next(m for m in months if m["month"] == 6)
        assert july["year"] == 2024
        assert july["expense_count"] == 3  # Coffee, Burger, Bus pass
        assert july["total"] == pytest.approx(46.50)
        assert june["expense_count"] == 2  # Netflix, Gym
        assert june["total"] == pytest.approx(60.99)

    def test_monthly_most_recent_first(self, seeded_client):
        client, _ = seeded_client
        months = client.get("/expenses/monthly").json()
        years_months = [(m["year"], m["month"]) for m in months]
        assert years_months == sorted(years_months, reverse=True)


# ---------------------------------------------------------------------------
# GET /expenses/{id}
# ---------------------------------------------------------------------------

class TestGetSingleExpense:
    def test_get_existing_expense(self, seeded_client):
        client, ids = seeded_client
        resp = client.get(f"/expenses/{ids[0]}")
        assert resp.status_code == 200
        assert resp.json()["id"] == ids[0]

    def test_get_nonexistent_expense_returns_404(self, client):
        resp = client.get("/expenses/00000000-0000-0000-0000-000000000000")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /expenses/{id}
# ---------------------------------------------------------------------------

class TestDeleteExpense:
    def test_delete_existing_expense(self, seeded_client):
        client, ids = seeded_client
        resp = client.delete(f"/expenses/{ids[0]}")
        assert resp.status_code == 204

    def test_deleted_expense_no_longer_listed(self, seeded_client):
        client, ids = seeded_client
        client.delete(f"/expenses/{ids[0]}")
        resp = client.get("/expenses/")
        all_ids = [e["id"] for e in resp.json()]
        assert ids[0] not in all_ids

    def test_delete_nonexistent_expense_returns_404(self, client):
        resp = client.delete("/expenses/00000000-0000-0000-0000-000000000000")
        assert resp.status_code == 404

    def test_double_delete_returns_404(self, seeded_client):
        client, ids = seeded_client
        client.delete(f"/expenses/{ids[0]}")
        resp = client.delete(f"/expenses/{ids[0]}")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

class TestRoot:
    def test_root_returns_200(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert "message" in resp.json()
