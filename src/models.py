"""
Pydantic models for request/response validation.
"""

from datetime import date as DateType
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class ExpenseCreate(BaseModel):
    """Payload accepted when creating a new expense."""

    title: str = Field(min_length=1, max_length=200, examples=["Coffee"])
    amount: float = Field(gt=0, examples=[4.50])
    category: str = Field(min_length=1, max_length=100, examples=["Food"])
    date: DateType = Field(examples=["2024-07-15"])

    @field_validator("title", "category", mode="before")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        return v.strip()

    @field_validator("amount", mode="before")
    @classmethod
    def round_amount(cls, v: float) -> float:
        return round(float(v), 2)


class Expense(ExpenseCreate):
    """An expense as stored and returned by the API."""

    id: str = Field(examples=["a1b2c3d4-e5f6-7890-abcd-ef1234567890"])

    model_config = {"from_attributes": True}


class TotalSummary(BaseModel):
    """Overall and per-category spending totals."""

    total: float
    by_category: dict[str, float]


class MonthlyEntry(BaseModel):
    year: int
    month: int
    total: float
    by_category: dict[str, float]
    expense_count: int


class SearchResult(BaseModel):
    query: str
    results: list[Expense]
    count: int
