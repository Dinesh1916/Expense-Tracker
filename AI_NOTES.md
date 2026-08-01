# AI Notes

This project was built with Claude (Anthropic) as a pair-programming aid. Here's an honest account of what came from the AI, what I validated, and what I changed.

---

## 1. Which parts were AI-generated vs. written by me

### AI-generated (then reviewed and edited)
- The initial skeleton of `src/models.py` — field definitions and validator structure
- The `Storage` class in `src/storage.py` — the in-memory dict approach, `_load`/`_save` methods, and the `override_storage` context manager pattern for test isolation
- The router in `src/routers/expenses.py` — endpoint signatures, dependency injection via `Depends(get_storage)`, and HTTP status codes
- The `conftest.py` fixture structure — the `mem_storage` / `client` / `seeded_client` layered fixture pattern
- Initial test method names and assertion structure in `test_expenses.py`

### Written or substantially rewritten by me
- The `override_storage` test-isolation pattern: I knew from experience that a module-level singleton would bleed between tests; I described the problem to the AI and then guided it toward the context-manager approach rather than accepting its first suggestion (monkey-patching `get_storage` directly, which was messier)
- The monthly summary logic in `storage.py` — the AI's first version used a `defaultdict` that lost `expense_count`; I rewrote it to a plain `dict[tuple, dict]` that tracks count alongside totals
- Test correctness: all expected numeric values (e.g. `107.49`, `46.50`, `16.50`) were calculated by hand and cross-checked against the seed data; several of the AI's initial assertions had off-by-one or rounding errors that I corrected

---

## 2. What I validated, tested, and changed

### Pydantic field-name clash (caught during testing)
The AI generated `from datetime import date` and then used `date` as a field name in the Pydantic model. In Pydantic v2 this causes a `PydanticUserError` because the annotation `date: date` shadows the imported type. I renamed the import to `DateType` to resolve it. The AI didn't flag this — I found it when running tests for the first time.

### Storage singleton isolation
The AI's first storage design used a module-level `_storage_instance` with no override hook. When I ran the tests they all shared the same store and polluted each other. I kept the singleton for the real server (so data persists across requests) but added the `_override` global + `override_storage()` context manager so tests can inject a clean in-memory instance per test. This pattern was my idea; the AI implemented it once I described what I wanted.

### Rounding accuracy
The AI used Python's built-in `sum()` directly over floats for the totals, which can accumulate floating-point drift. I changed the totals logic to round to 2 d.p. at each accumulation step (`round(..., 2)`) and use `pytest.approx` in the assertions. Small thing, but it matters for a money tracker.

### Sort order
The AI's initial `get_all()` returned expenses in insertion order. I added `sorted(..., key=lambda e: e.date, reverse=True)` so newer expenses surface first — more useful UX and something the tests now explicitly verify.

---

## 3. AI suggestions I decided not to use

### SQLite instead of JSON
The AI repeatedly suggested SQLite (via `sqlite3` or SQLAlchemy) as "more robust". I declined because:
1. The spec explicitly says "in memory or a local JSON file; no database required"
2. SQLite adds dependencies and setup friction; the human reviewer should be able to run `pip install -r requirements.txt && uvicorn src.main:app` with no extra steps
3. A flat JSON file is perfectly sufficient for the scale described

### Separate `PUT /expenses/{id}` update endpoint
The AI offered to add an update endpoint. I left it out because the spec doesn't list it, and adding unasked-for scope can obscure whether the core requirements are solid. If it were a real project I'd add it.

### Async SQLAlchemy with `async def` endpoints
The AI suggested making all route handlers `async def` with `asyncio`. Since the storage layer is synchronous file I/O and there are no network calls, making the handlers async would add complexity with no benefit. I kept everything synchronous.

### Pydantic `model_config = {"json_schema_extra": {"examples": [...]}}` per endpoint
The AI generated elaborate per-endpoint OpenAPI example bodies. I simplified to inline `examples=` on each `Field(...)` — same effect, less noise.
