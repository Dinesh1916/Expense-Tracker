"""
JSON-file-backed storage for expenses.

All persistence lives in a single JSON file (data/expenses.json).
The module exposes a singleton Storage instance via get_storage().
Tests inject an in-memory override via override_storage().
"""

import json
import os
import uuid
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from typing import Optional

from .models import Expense, ExpenseCreate

_DATA_FILE = Path(__file__).parent.parent / "data" / "expenses.json"

# Singleton + test-override mechanism
_storage_instance: Optional["Storage"] = None
_override: Optional["Storage"] = None


class Storage:
    """Thread-safe (for a single-process dev server) in-memory store that
    optionally syncs to a JSON file on disk."""

    def __init__(self, filepath: Optional[Path] = None):
        self._filepath = filepath
        self._expenses: dict[str, Expense] = {}
        if filepath:
            self._load()

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------

    def _load(self) -> None:
        if self._filepath and self._filepath.exists():
            raw = json.loads(self._filepath.read_text(encoding="utf-8"))
            self._expenses = {
                item["id"]: Expense(**item) for item in raw
            }

    def _save(self) -> None:
        if self._filepath:
            self._filepath.parent.mkdir(parents=True, exist_ok=True)
            data = [e.model_dump(mode="json") for e in self._expenses.values()]
            self._filepath.write_text(
                json.dumps(data, indent=2, default=str), encoding="utf-8"
            )

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def add(self, payload: ExpenseCreate) -> Expense:
        expense_id = str(uuid.uuid4())
        expense = Expense(id=expense_id, **payload.model_dump())
        self._expenses[expense_id] = expense
        self._save()
        return expense

    def get_all(self) -> list[Expense]:
        return sorted(self._expenses.values(), key=lambda e: e.date, reverse=True)

    def get_by_id(self, expense_id: str) -> Optional[Expense]:
        return self._expenses.get(expense_id)

    def delete(self, expense_id: str) -> bool:
        if expense_id not in self._expenses:
            return False
        del self._expenses[expense_id]
        self._save()
        return True

    def filter_by_category(self, category: str) -> list[Expense]:
        cat = category.lower()
        return sorted(
            [e for e in self._expenses.values() if e.category.lower() == cat],
            key=lambda e: e.date,
            reverse=True,
        )

    def search(self, query: str) -> list[Expense]:
        q = query.lower()
        return sorted(
            [
                e
                for e in self._expenses.values()
                if q in e.title.lower() or q in e.category.lower()
            ],
            key=lambda e: e.date,
            reverse=True,
        )

    def totals(self) -> tuple[float, dict[str, float]]:
        by_cat: dict[str, float] = {}
        for e in self._expenses.values():
            by_cat[e.category] = round(by_cat.get(e.category, 0.0) + e.amount, 2)
        total = round(sum(by_cat.values()), 2)
        return total, by_cat

    def monthly_summary(self) -> list[dict]:
        months: dict[tuple[int, int], dict] = {}
        for e in self._expenses.values():
            key = (e.date.year, e.date.month)
            if key not in months:
                months[key] = {"year": key[0], "month": key[1], "total": 0.0, "by_category": {}, "expense_count": 0}
            entry = months[key]
            entry["total"] = round(entry["total"] + e.amount, 2)
            entry["by_category"][e.category] = round(
                entry["by_category"].get(e.category, 0.0) + e.amount, 2
            )
            entry["expense_count"] += 1
        return sorted(months.values(), key=lambda m: (m["year"], m["month"]), reverse=True)

    def clear(self) -> None:
        """Remove all expenses (used by tests)."""
        self._expenses.clear()
        self._save()


def get_storage() -> Storage:
    """Return the active Storage instance (respects test overrides)."""
    global _storage_instance
    if _override is not None:
        return _override
    if _storage_instance is None:
        _storage_instance = Storage(filepath=_DATA_FILE)
    return _storage_instance


@contextmanager
def override_storage(storage: Storage):
    """Context manager that temporarily swaps the storage singleton.
    Used exclusively in tests."""
    global _override
    _override = storage
    try:
        yield storage
    finally:
        _override = None
