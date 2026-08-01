"""
Expense router — all /expenses endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ..models import Expense, ExpenseCreate, MonthlyEntry, SearchResult, TotalSummary
from ..storage import Storage, get_storage

router = APIRouter(prefix="/expenses", tags=["expenses"])


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------

@router.post(
    "/",
    response_model=Expense,
    status_code=status.HTTP_201_CREATED,
    summary="Add a new expense",
)
def create_expense(
    payload: ExpenseCreate,
    storage: Storage = Depends(get_storage),
) -> Expense:
    """Add a new expense record. Returns the created expense with its generated `id`."""
    return storage.add(payload)


# ---------------------------------------------------------------------------
# Read — list / filter
# ---------------------------------------------------------------------------

@router.get(
    "/",
    response_model=list[Expense],
    summary="List all expenses",
)
def list_expenses(
    category: str | None = Query(
        default=None,
        description="Filter by category (case-insensitive)",
    ),
    storage: Storage = Depends(get_storage),
) -> list[Expense]:
    """Return all expenses, optionally filtered to a single category."""
    if category is not None:
        return storage.filter_by_category(category)
    return storage.get_all()


@router.get(
    "/search",
    response_model=SearchResult,
    summary="Search expenses by keyword",
)
def search_expenses(
    q: str = Query(..., min_length=1, description="Keyword to search in title or category"),
    storage: Storage = Depends(get_storage),
) -> SearchResult:
    """Search expenses whose title **or** category contains the given keyword (case-insensitive)."""
    results = storage.search(q)
    return SearchResult(query=q, results=results, count=len(results))


# ---------------------------------------------------------------------------
# Totals / summaries
# ---------------------------------------------------------------------------

@router.get(
    "/totals",
    response_model=TotalSummary,
    summary="Get spending totals",
)
def get_totals(storage: Storage = Depends(get_storage)) -> TotalSummary:
    """Return the overall total and a breakdown of spending by category."""
    total, by_category = storage.totals()
    return TotalSummary(total=total, by_category=by_category)


@router.get(
    "/monthly",
    response_model=list[MonthlyEntry],
    summary="Monthly spending summary",
)
def monthly_summary(storage: Storage = Depends(get_storage)) -> list[MonthlyEntry]:
    """Return a month-by-month spending summary, most recent first."""
    return storage.monthly_summary()


# ---------------------------------------------------------------------------
# Read — single
# ---------------------------------------------------------------------------

@router.get(
    "/{expense_id}",
    response_model=Expense,
    summary="Get a single expense",
)
def get_expense(
    expense_id: str,
    storage: Storage = Depends(get_storage),
) -> Expense:
    """Retrieve a single expense by its UUID."""
    expense = storage.get_by_id(expense_id)
    if expense is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Expense '{expense_id}' not found.",
        )
    return expense


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------

@router.delete(
    "/{expense_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an expense",
)
def delete_expense(
    expense_id: str,
    storage: Storage = Depends(get_storage),
) -> None:
    """Permanently delete an expense by its UUID."""
    deleted = storage.delete(expense_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Expense '{expense_id}' not found.",
        )
