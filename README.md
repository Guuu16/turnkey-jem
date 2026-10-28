# Full-Stack Coding Assessment

Chinese version: [README.zh-CN.md](README.zh-CN.md)

Repository: <https://github.com/Guuu16/turnkey-jem>

## Project Overview

This repository contains the Task A and Task B implementations, the Task C answers, and a runnable full-stack application (FastAPI + SQLite backend, Next.js + TypeScript frontend). The primary documentation and source comments are written in English; a Chinese translation of this root README is available at [README.zh-CN.md](README.zh-CN.md).

## Assessment Requirements

The section below restates the assessment brief in English so the required scope and acceptance points are visible before reviewing the implementation.

### Submission Requirements

- Submit an accessible GitHub or GitLab repository.
- Include the required top-level directories: `A/`, `B/`, `C/`, and `app/`.
- Include a root `README.md` with startup steps, run commands, assumptions, architecture, and known limitations.
- Include automated tests, and make sure every test can be run using commands documented in the README.
- Never commit credentials, tokens, real customer data, or personal data.
- Disclose where AI tools were used and be prepared to explain or modify every submitted decision.
- Put correctness, readability, and maintainability ahead of unnecessary complexity.
- Validate input and make failure behavior explicit.
- List standard-library and third-party dependencies clearly.

### Task A: Inventory Reservation Ledger (20 points)

Implement a deterministic command processor for one SKU. The ledger tracks `on_hand`, `reserved`, and processed event IDs. Available stock is `on_hand - reserved`.

Input starts with one header containing initial stock `S` and command count `N`, followed by `N` commands:

```text
RESERVE event_id order_id qty
RELEASE event_id order_id qty
SHIP event_id order_id qty
RESTOCK event_id qty
```

Required behavior:

- Every quantity must be a positive integer.
- Reject malformed input without partially changing state.
- `RESERVE` succeeds only when enough stock is available.
- `RELEASE` and `SHIP` cannot exceed the quantity currently reserved for that order.
- `SHIP` decreases both `on_hand` and the order's reserved quantity.
- Every `event_id` is idempotent. Replaying a processed event returns `DUPLICATE` and must not change state.
- An event rejected by a business rule is still considered processed for idempotency purposes.

For each command, output `OK`, `REJECTED`, or `DUPLICATE`, followed by the current `on_hand` and total `reserved` values. After all commands, output the open reservations sorted by `order_id`.

Constraints:

```text
0 <= S <= 10^12
1 <= N <= 200,000
1 <= qty <= 10^12
event_id and order_id are non-empty ASCII tokens
```

Required deliverables: an executable Python program, boundary and replay tests, and a short complexity analysis.

### Task B: Fulfilment Split Optimizer (20 points)

Choose a warehouse allocation that fulfils exactly `Q` units and optimizes the following criteria in order:

1. Minimize the number of warehouses used.
2. Minimize total cost, where each used warehouse contributes `fixed_cost + allocated_qty * unit_cost`.
3. Choose the lexicographically smallest allocation list ordered by `warehouse_id`.

Input format:

```text
W Q
warehouse_id stock fixed_cost unit_cost
```

The warehouse line is repeated `W` times.

Constraints:

```text
1 <= W <= 30
1 <= Q <= 2,000
0 <= stock <= 2,000
0 <= fixed_cost, unit_cost <= 10^6
sum(stock) may be less than Q
```

Output requirements:

- If the order cannot be fulfilled, print `1`.
- Otherwise print the number of warehouses used and the total cost on the first line.
- Then print each used warehouse and its allocated quantity, sorted by `warehouse_id`.

The solution must scale beyond exhaustive subset search, use only the Python standard library, and document the state representation, tie-breaking strategy, and time/space complexity. Tests must cover impossible orders, zero-stock warehouses, equal-cost ties, and large quantities.

### Task C: Xero Integration Review (20 points)

Answer in concise Markdown. Cover observable checks, failure handling, and production-safe behavior. Code snippets or pseudocode may be used where helpful. The scenario is a multi-tenant service syncing invoices between an internal order system and Xero in a background worker. Tokens, tenant IDs, and sync cursors are stored per connected organization.

- **C1 - Connection verification:** Before reading invoices, describe the minimum calls and checks that prove OAuth and tenant selection work, and explain what each result proves.
- **C2 - Failure diagnosis:** When `connections` succeeds but `invoices` returns 401, 403, or 404 in different environments, provide a decision tree covering expired tokens, scopes, tenant headers or IDs, permissions, and environment configuration.
- **C3 - Incremental sync:** Design a recoverable invoice sync for a large organization, including pagination, change windows or `modified-since` behavior, cursor persistence, duplicates, partial failures, and safe replay.
- **C4 - Rate limiting:** When a worker receives HTTP 429, explain response headers, backoff and jitter, concurrency limits, retry budgets, scheduling, and errors that must not be retried.
- **C5 - Data integrity:** Prevent duplicate invoices when a create-invoice request times out and is retried, and explain reconciliation when Xero succeeded but the response was lost.
- **C6 - Observability and security:** List required logs, metrics, alerts, and correlation identifiers. Explain what must never be logged and how secrets and tokens should be stored and rotated.

Use current official Xero developer documentation, link the referenced pages, and state assumptions about SDK or API versions.

### Full-Stack Application: Variant Product Detail Page (40 points)

Build a production-aware product detail page (PDP) and backend API. The assessment focuses on end-to-end behavior rather than visual polish alone.

Required stack:

- Python 3.11+ and FastAPI for the backend.
- React and TypeScript for the frontend. Next.js or Vite may be used.
- In-memory storage or SQLite. Seed data must make the application usable immediately after startup.

Domain model requirements:

- One product with at least two option dimensions, such as color and size.
- At least six SKUs.
- Include one unavailable combination and one out-of-stock SKU.
- Each SKU must have its own ID, price, available quantity, image, and option values.

Required API:

| Method | Endpoint | Required behavior |
| --- | --- | --- |
| GET | `/api/products/{id}` | Return product, option, and SKU data |
| POST | `/api/cart/items` | Add a SKU and quantity to the cart |
| GET | `/api/cart` | Return the current cart and total item count |

Backend requirements:

- Validate SKU existence, quantity, and current stock on the server.
- Never trust client-provided price or stock data.
- Accept an `Idempotency-Key` on add-to-cart requests and prevent duplicate additions for the same key.
- Return structured errors for invalid input, insufficient stock, and unexpected failures.
- Prevent overselling when concurrent requests compete for the last unit, and explain the approach.
- Test success, validation, idempotency, and stock races.
- Document request/response examples and status codes. OpenAPI output supplements but does not replace this contract.

Frontend requirements:

- Display the product image, name, description, selected price, stock status, and cart count.
- Render two option dimensions and visibly disable impossible or unavailable combinations.
- Resolve the selected SKU on option changes and update price, image, and stock without stale UI.
- Keep quantity within `1` and the available stock, including after the selected SKU changes.
- Show a loading state on add-to-cart and prevent accidental duplicate submission.
- Expose success and error feedback accessibly.
- Cover initial loading, retryable product-load failure, incomplete selection, invalid combination, out-of-stock SKU, adding, success, validation failure, insufficient stock, and server error states.
- Work at approximately `375px` and `1280px` widths.
- Support keyboard operation, visible focus, semantic labels, and assistive-technology announcements.
- Avoid unnecessary TypeScript `any` usage and separate API, domain, and UI concerns.
- Include at least three meaningful frontend tests, including variant resolution and double-click prevention.
- Recover without a full-page refresh when requests are delayed, fail, or return newer stock than the initial product response.

Authentication, checkout, payment processing, and production deployment are out of scope. Optional extensions include optimistic UI with a rollback strategy, privacy-safe `view_item`, `select_item`, and `add_to_cart` analytics, and containerization or a one-command local startup.

### Scoring and Final Checks

| Area | Scoring focus | Points |
| --- | --- | --- |
| Task A | Correct state transitions, idempotency, validation, O(N) processing, high-value tests | 20 |
| Task B | Correct optimization and tie-breaking, scalable DP, clear complexity analysis | 20 |
| Task C | Accurate diagnosis, recoverable sync, restrained retries, integrity, security, observability | 20 |
| Backend | Clear contract, server-side rules, concurrency safety, idempotency, structured errors, tests | 20 |
| Frontend | Correct SKU state, resilient async UX, accessibility, TypeScript design, focused tests | 15 |
| Delivery | Easy startup, clean repository, documented trade-offs and limitations | 5 |

Before submission, verify repository access, test every startup command, run all automated tests, document assumptions, disclose AI usage, and confirm that no secrets were committed.

## Submission Map

- Task A implementation and documentation: [A/README.md](A/README.md)
- Task B implementation and documentation: [B/README.md](B/README.md)
- Full-stack application documentation and API contract: [app/README.md](app/README.md)
- Task C answers (English), including C1-C6 Python-style pseudocode: [C/answers.md](C/answers.md)

## Repository Structure

```text
turnkey-jem/
├── .gitignore
├── A/
│   ├── README.md
│   ├── src/
│   └── tests/
├── B/
│   ├── README.md
│   ├── src/
│   └── tests/
├── app/
│   ├── README.md
│   ├── backend/
│   │   ├── app/
│   │   ├── tests/
│   │   └── requirements.txt
│   └── frontend/
│       ├── app/
│       ├── components/
│       ├── docs/
│       └── lib/
├── C/
│   ├── answers.md
│   ├── tests/
│   └── screenshots/
├── requirements.txt
├── README.md
└── README.zh-CN.md
```

## Architecture

`A/` is a deterministic, single-process inventory state machine whose core state is `on_hand`, `reserved`, and processed event IDs.

`B/` first uses one-dimensional DP to minimise warehouse count and cost, then reconstructs the lexicographically smallest allocation in warehouse-ID order.

`C/` is the Xero multi-tenant sync design review covering connection verification, failure classification, incremental cursors, rate limits, idempotent invoicing, observability, and secret rotation.

`app/` server-renders the initial product data with Next.js, calls FastAPI through same-origin `/api/*`, and lets FastAPI own price, stock, cart, and idempotency state in SQLite transactions.

## Run Tests

Create a Python 3.11+ test environment at the repository root and install dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Run the Task A tests from the repository root:

```powershell
Push-Location A
..\.venv\Scripts\python.exe -m pytest -q
Pop-Location
```

Run the Task B tests from the repository root:

```powershell
Push-Location B
..\.venv\Scripts\python.exe -m pytest -q
Pop-Location
```

Run linting and formatting checks:

```powershell
Push-Location A
..\.venv\Scripts\python.exe -m ruff check src tests
..\.venv\Scripts\python.exe -m ruff format --check src tests
Pop-Location

Push-Location B
..\.venv\Scripts\python.exe -m ruff check src tests
..\.venv\Scripts\python.exe -m ruff format --check src tests
Pop-Location
```

Run the Task C pseudocode contract tests:

```powershell
Push-Location C
..\.venv\Scripts\python.exe -m pytest -q
Pop-Location
```

### macOS Terminal

macOS needs Python 3.11+ and Node.js 20.9+ with npm.

Run these commands from the repository root:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt

cd A
../.venv/bin/python -m pytest -q
../.venv/bin/python -m ruff check src tests
../.venv/bin/python -m ruff format --check src tests
cd ..

cd B
../.venv/bin/python -m pytest -q
../.venv/bin/python -m ruff check src tests
../.venv/bin/python -m ruff format --check src tests
cd ..

cd C
../.venv/bin/python -m pytest -q
cd ..
```

## Run the Full-Stack App

Start the API first (it creates and seeds the SQLite database on first run):

```powershell
Push-Location app\backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
Pop-Location
```

Then start the frontend and open <http://127.0.0.1:3000>:

```powershell
Push-Location app\frontend
npm install
npm run dev
Pop-Location
```

Run the full-stack app tests and checks:

```powershell
Push-Location app\backend
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check app tests
.\.venv\Scripts\python.exe -m ruff format --check app tests
Pop-Location

Push-Location app\frontend
npm run typecheck
npm test
npm run build
Pop-Location
```

On macOS, use two Terminal windows. Start the API in the first:

```bash
cd app/backend
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Start the frontend in the second:

```bash
cd app/frontend
npm install
npm run dev
```

To run the full-stack checks on macOS:

```bash
cd app/backend
.venv/bin/python -m pytest -q
.venv/bin/python -m ruff check app tests
.venv/bin/python -m ruff format --check app tests
cd ../frontend
npm test
npm run typecheck
npm run build
```

The backend suite contains `33` tests and the frontend suite contains `15`.
Frontend responsive QA was browser-verified at `375×812` and `1280×800`; the
mobile layout stacks cleanly and the desktop layout uses two columns without
horizontal overflow. Screenshots: [375×812](app/frontend/docs/responsive-375x812.png)
and [1280×800](app/frontend/docs/responsive-1280x800.png).

The API contract, error codes, idempotency and oversell-prevention design are in [app/README.md](app/README.md).

## AI Usage

- I used AI to translate the tasks, clarify constraints, and break down the scoring objectives.
- I used AI to help design happy-path, boundary, invalid-input, and randomised differential tests.
- I used AI to compare algorithm options, review implementations, and simplify the code structure.
- I used AI to help explain the code logic and prepare the English documentation.
- I verified the final results with project tests, Ruff, formatting checks, and manual examples.
- AI processed only synthetic data from this coding assessment; no credentials, customer data, or personal information were used.

## Dependencies

- The task executables use only the Python standard library.
- `pytest` and `ruff` are project dependencies used only for development and verification.
- All dependencies are listed in [requirements.txt](requirements.txt).
- The full-stack app dependencies are listed in [app/backend/requirements.txt](app/backend/requirements.txt), [app/backend/requirements-dev.txt](app/backend/requirements-dev.txt) and [app/frontend/package.json](app/frontend/package.json).

## Assumptions and Known Limitations

- Task B follows the literal specification: `Q >= 1`, and an impossible order prints `1`.
- Task C delivers executable Python-style pseudocode and review notes; it does not call a real Xero tenant or store real credentials.
- The full-stack app has one demo cart and does not include authentication, checkout, payment, or production deployment.
- Stock is reserved immediately when an item is added to the cart; reservation expiry and background release are not implemented.
- SQLite is appropriate for this single-host assessment; a multi-node production deployment would move the same conditional update and idempotency rules to a shared database.
- Idempotency records currently have no retention window, and the catalogue is seed data without an admin API.
