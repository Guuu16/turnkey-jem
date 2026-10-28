# Task B - Fulfilment Split Optimiser

## Problem Statement

An order may be fulfilled by multiple warehouses. Allocate exactly `Q` units and choose the optimal solution required by the task.

### Input

```text
W Q
warehouse_id stock fixed_cost unit_cost
... repeated exactly W times
```

- `W` is the number of warehouses and `Q` is the total quantity to allocate.
- The warehouse record format shown on the second line must appear exactly `W` times.

### Warehouse Fields

- `warehouse_id` is the unique warehouse identifier, such as `AU`, `CN`, or `US`.
- `stock` is the maximum quantity available from that warehouse, so its allocation must be in `0..stock`.
- `fixed_cost` is charged once whenever the warehouse is used and is not charged when its allocation is 0.
- `unit_cost` is charged for every unit allocated from that warehouse.
- If `q > 0` units are allocated from a warehouse, its cost is `fixed_cost + q * unit_cost`.

### Optimisation Priority

All feasible solutions are compared using the following three objectives in order.

1. Minimise the number of warehouses used.
2. Minimise total cost, which is the sum of the costs of all used warehouses.
3. If the first two objectives tie, choose the lexicographically smallest allocation list sorted by `warehouse_id`.

### Constraints

```text
1 <= W <= 30
1 <= Q <= 2000
0 <= stock <= 2000
0 <= fixed_cost <= 10^6
0 <= unit_cost <= 10^6
```

Warehouse IDs are non-empty ASCII tokens.

### Output

- Print `1` when exactly `Q` units cannot be fulfilled.
- Otherwise, print `warehouse_count total_cost` on the first line.
- Then print each used `warehouse_id allocated_qty` on its own line, sorted by warehouse ID.

### Example

```text
Input
3 7
AU 5 8 2
CN 7 20 1
US 4 3 4

Output
1 27
CN 7
```

`CN` alone can fulfil 7 units at cost `20 + 7 * 1 = 27` and also achieves the minimum warehouse count.

## Test Approach

- Verify the specification example, exact fulfilment, and impossible orders.
- Verify fixed-cost, unit-cost, warehouse-count priority, and lexicographic tie-breaking separately.
- Cover the maximum quantity with one warehouse and with many required warehouses.
- Invalid-input tests cover headers, field counts, numeric ranges including `Q == 0`, ASCII IDs, and duplicate IDs.
- Compare seeded small random cases against a brute-force oracle.
- Test data lives in `tests/fulfilment_cases.py`, separate from execution logic.

## Dynamic Programming

- Sort warehouses by `warehouse_id` first so reconstruction and output order are deterministic.
- The maximum possible total cost is `30 * 10^6 + 2000 * 10^6 = 2,030,000,000`.
- Set the weight to `maximum total cost + 1`, then `score = used * weight + cost` stores both warehouse count and cost.
- `dp[amount]` is the minimum `score` for allocating exactly `amount` units.
- If warehouse `i` is not used, states are copied from suffix `i + 1`.
- If it is used for `q > 0` units, the score increases by `weight + fixed_cost + q * unit_cost`.
- Unit cost is linear, so a monotonic deque maintains the sliding-window minimum instead of enumerating every previous quantity.
- The final `dp[Q]` automatically prioritises the minimum warehouse count, then the minimum cost.

## Tie-Breaking

- Reconstruct in warehouse-ID order and prefer the current warehouse whenever the optimal score remains unchanged.
- Once a warehouse is selected, choose the smallest allocation that still preserves the optimal score.
- This produces the lexicographically smallest result when comparing `(warehouse_id, allocated_qty)` pairs.

## Complexity

- Time complexity is `O(W * Q)`.
- Space complexity is `O(W * Q)` because all one-dimensional suffix DP tables are retained for reconstruction.

## Dependencies

- The executable uses only the Python standard library: `sys`, `collections`, and `dataclasses`.
- `pytest` is used only for parameterised tests, and `ruff` is used only for linting and formatting checks.
- No third-party package is required to run `src/fulfilment.py`.
- Development and test dependencies are listed explicitly in the project root `requirements.txt`.

## Run

```powershell
..\.venv\Scripts\python.exe -m pytest -q
..\.venv\Scripts\python.exe -m ruff check src tests
..\.venv\Scripts\python.exe -m ruff format --check src tests
..\.venv\Scripts\python.exe src\fulfilment.py < input.txt
```
