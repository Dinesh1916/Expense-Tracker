# AI_NOTES

## 1. Which parts were AI-generated vs. written by me

**Written by me**

The architecture and all core decisions were mine. I designed the project structure, chose the storage approach (in-memory dict with JSON persistence), planned the API surface, and wrote the test strategy before involving any AI tools.

- `src/models.py` — I defined the fields, types, and validation rules. I used AI to generate the initial boilerplate from my spec, then rewrote the validators and caught a Pydantic v2 name clash the AI missed (see Section 2).
- `src/storage.py` — I designed the singleton pattern, the `_load`/`_save` lifecycle, and the `override_storage` context manager for test isolation. The test-isolation problem was something I anticipated from experience; AI didn't suggest it.
- `src/routers/expenses.py` — I decided the endpoint structure, status codes, and dependency injection approach. AI helped draft the boilerplate once I had the design.
- `conftest.py` and `test_expenses.py` — I wrote the test strategy and all expected values by hand. AI helped scaffold repetitive fixture setup; I wrote and verified every assertion.
- Monthly summary logic in `storage.py` — written entirely by me after the AI's version didn't track `expense_count` correctly (see Section 2).

**Where I used AI as a tool**

I used Claude to generate boilerplate from my descriptions — endpoint signatures, fixture scaffolding, and model field syntax. In every case I reviewed the output, ran the tests, and rewrote anything that didn't meet my requirements. AI was used like autocomplete for the parts I already knew how to write; the decisions and the verification were mine.

---

## 2. What I validated, tested, or changed — and why

**Pydantic field-name clash**

I ran into a `PydanticUserError` on the first test run — `date: date` shadows the imported type in Pydantic v2. The AI hadn't flagged it. I renamed the import to `DateType` to fix it.

**Test isolation via `override_storage`**

I knew from the start that a module-level singleton would bleed state between tests. I designed the `_override` global and `override_storage()` context manager myself so each test gets a clean in-memory instance. Without it, every test in the suite would share the same store and pollute each other. The AI's first design had no override hook at all.

**Monthly summary rewrite**

The AI's version used a `defaultdict` that silently dropped `expense_count` during aggregation. I rewrote it to a plain `dict[tuple, dict]` that tracks count alongside totals — easier to reason about and correct.

**Rounding**

`sum()` over floats drifts. I changed the totals logic to `round(..., 2)` at each accumulation step and used `pytest.approx` in assertions. Matters for a money tracker.

**Sort order**

I added `sorted(..., key=lambda e: e.date, reverse=True)` to `get_all()` so newer expenses surface first. The AI returned insertion order, which is the wrong default for this use case. Tests now verify the sort explicitly.

**All numeric assertions**

Every expected value in the tests (`107.49`, `46.50`, `16.50`, etc.) was calculated by hand against the seed data. Several of the AI's generated assertions were wrong — off-by-one errors and rounding mistakes that I caught and corrected.

---

## 3. AI suggestions I decided not to use — and why

**SQLite instead of JSON**

AI pushed SQLite repeatedly. I declined — the spec says "in memory or a local JSON file; no database required." SQLite adds dependencies and setup friction for no real gain at this scale. Anyone reviewing this should be able to run `pip install -r requirements.txt && uvicorn src.main:app` and be done.

**`PUT /expenses/{id}` update endpoint**

AI offered to add one. I left it out because it's not in the spec. Adding unasked-for scope makes it harder to see whether the core requirements are solid.

**Async route handlers**

AI suggested `async def` with asyncio throughout. The storage layer is synchronous file I/O with no network calls — making handlers async would add complexity with nothing to show for it. I kept everything synchronous.

**Verbose OpenAPI example blocks**

AI generated `model_config = {"json_schema_extra": {"examples": [...]}}` per endpoint. I replaced that with inline `examples=` on each `Field(...)` — same result in the generated docs, far less noise in the code.
