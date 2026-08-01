"""
Smart Expense Tracker API
FastAPI application entry point.
"""

from fastapi import FastAPI

from .routers import expenses

app = FastAPI(
    title="Smart Expense Tracker",
    description=(
        "A REST API to manage personal expenses. "
        "Supports adding, viewing, filtering, summarising, and deleting expenses."
    ),
    version="1.0.0",
)

app.include_router(expenses.router)


@app.get("/", tags=["health"])
def root():
    """Health check / welcome endpoint."""
    return {"message": "Smart Expense Tracker API is running", "docs": "/docs"}
