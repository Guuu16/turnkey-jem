# Task A - Inventory Reservation Ledger

## Problem Statement

Implement an inventory reservation ledger using the specified data structures, tracking current stock and reserved quantities while processing order reservations, releases, and shipments.

### Input

```text
S N
COMMAND
... repeated exactly N times
```

`S` is the initial stock and `N` is the number of commands.

The command formats are:

```text
RESERVE event_id order_id qty
RELEASE event_id order_id qty
SHIP event_id order_id qty
RESTOCK event_id qty
```

- `event_id` is the unique event identifier for the command.
- `order_id` is the order identifier.
- `qty` is the quantity to reserve, release, ship, or restock.

### Rules

- All quantities must be positive integers.
- A malformed command must be rejected without producing any partial state change.
- `RESERVE` can succeed only when available stock is sufficient.
- The quantity for `RELEASE` or `SHIP` cannot exceed the order's current reservation.
- `SHIP` reduces both on-hand stock and the order's reserved quantity.
- `RESTOCK` only increases on-hand stock.
- Every `event_id` is idempotent; a duplicate event returns `DUPLICATE` and changes no state.
- A command rejected by a business rule still records its event ID.

### Constraints

```text
0 <= S <= 10^12
1 <= N <= 200,000
1 <= qty <= 10^12
```

`event_id` and `order_id` are non-empty ASCII tokens.

### Output

- Each command outputs `STATUS on_hand reserved`.
- `STATUS` is `OK`, `REJECTED`, or `DUPLICATE`.
- After all commands are processed, output `OPEN count`.
- Then list each order with an open reservation and its quantity, sorted by `order_id`.

### Example

```text
Input
10 5
RESERVE E1 O1 3
RESERVE E1 O2 2
RESERVE E2 O2 2
RELEASE E3 O1 1
SHIP E4 O1 2

Output
OK 10 3
DUPLICATE 10 3
OK 10 5
OK 10 4
OK 8 2
OPEN 1
O2 2
```

## Test Approach

- Verify one complete command sequence first, covering input, state changes, and output format.
- Verify the happy path for reserve, release, ship, and restock separately.
- Verify rejection when stock is insufficient or a release or shipment exceeds the order reservation.
- Verify that duplicate events do not change stock twice.
- Verify that business rejections consume an event ID while malformed commands do not.
- Verify that open reservations are sorted by order ID and that no reservations produce `OPEN 0`.

## Complexity

- Each command uses constant time, and final sorting is `O(N + O log O)`.
- Space complexity is `O(E + O)`.

## Dependencies

- The executable uses only the Python standard library.
- `pytest` is used only for tests, and `ruff` is used only for linting and formatting checks.
- Development and test dependencies are listed explicitly in the project root `requirements.txt`.

## Run

```powershell
..\.venv\Scripts\python.exe -m pytest -q
..\.venv\Scripts\python.exe -m ruff check src tests
..\.venv\Scripts\python.exe -m ruff format --check src tests
..\.venv\Scripts\python.exe src\inventory_ledger.py < input.txt
```

macOS Terminal:

```bash
../.venv/bin/python -m pytest -q
../.venv/bin/python -m ruff check src tests
../.venv/bin/python -m ruff format --check src tests
../.venv/bin/python src/inventory_ledger.py < input.txt
```
