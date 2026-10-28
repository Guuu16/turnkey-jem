"""Fulfilment split optimiser.

Input:
    W Q
    warehouse_id stock fixed_cost unit_cost  # repeated W times

Fields:
    warehouse_id: unique warehouse identifier
    stock: maximum quantity available
    fixed_cost: charged once when used
    unit_cost: charged per allocated unit

Objective, in priority order:
    1. Minimise warehouse count
    2. Minimise total cost
    3. Lexicographically smallest allocation list sorted by ID

Output:
    1 when fulfilment is impossible
    warehouse_count total_cost, followed by used warehouses and quantities
"""

from __future__ import annotations

import sys
from collections import deque
from dataclasses import dataclass

MAX_WAREHOUSES = 30
MAX_QUANTITY = 2000
MAX_COST = 1000000
MAX_TOTAL_COST = MAX_WAREHOUSES * MAX_COST + MAX_QUANTITY * MAX_COST
COUNT_WEIGHT = MAX_TOTAL_COST + 1
INFINITY = 10**30


@dataclass(frozen=True)
class Warehouse:
    warehouse_id: str
    stock: int
    fixed_cost: int
    unit_cost: int


def parse_integer(token: str, minimum: int, maximum: int, name: str) -> int:
    """Parse a decimal integer within the inclusive range."""
    if not (token.isascii() and token.isdigit()):
        raise ValueError(f"invalid {name}")

    value = int(token)
    if not minimum <= value <= maximum:
        raise ValueError(f"{name} is out of range")
    return value


def parse_input(input_text: str) -> tuple[int, list[Warehouse]]:
    """Parse and validate the complete input document."""
    lines = input_text.splitlines()
    if not lines:
        raise ValueError("missing header")

    header = lines[0].split()
    if len(header) != 2:
        raise ValueError("invalid header")

    warehouse_count = parse_integer(header[0], 1, MAX_WAREHOUSES, "warehouse count")
    quantity = parse_integer(header[1], 1, MAX_QUANTITY, "requested quantity")
    rows = lines[1:]
    if len(rows) != warehouse_count:
        raise ValueError("warehouse row count does not match header")

    warehouses: list[Warehouse] = []
    seen_ids: set[str] = set()
    for row in rows:
        parts = row.split()
        if len(parts) != 4:
            raise ValueError("invalid warehouse row")

        warehouse_id = parts[0]
        if not is_ascii_token(warehouse_id):
            raise ValueError("invalid warehouse id")
        if warehouse_id in seen_ids:
            raise ValueError("duplicate warehouse id")
        seen_ids.add(warehouse_id)

        warehouses.append(
            Warehouse(
                warehouse_id=warehouse_id,
                stock=parse_integer(parts[1], 0, MAX_QUANTITY, "stock"),
                fixed_cost=parse_integer(parts[2], 0, MAX_COST, "fixed cost"),
                unit_cost=parse_integer(parts[3], 0, MAX_COST, "unit cost"),
            )
        )

    warehouses.sort(key=lambda warehouse: warehouse.warehouse_id)
    return quantity, warehouses


def is_ascii_token(token: str) -> bool:
    return bool(token) and all(33 <= ord(char) <= 126 for char in token)


def build_best_scores(
    warehouses: list[Warehouse],
    quantity: int,
) -> list[list[int]]:
    warehouse_count = len(warehouses)
    suffix_scores: list[list[int]] = [[] for _ in range(warehouse_count + 1)]

    base = [INFINITY] * (quantity + 1)
    base[0] = 0
    suffix_scores[warehouse_count] = base

    for index in range(warehouse_count - 1, -1, -1):
        warehouse = warehouses[index]
        following = suffix_scores[index + 1]
        current = following[:]

        if warehouse.stock > 0:
            minimums: deque[tuple[int, int]] = deque()
            for required in range(1, quantity + 1):
                previous = required - 1
                if following[previous] < INFINITY:
                    adjusted = following[previous] - previous * warehouse.unit_cost
                    while minimums and minimums[-1][1] >= adjusted:
                        minimums.pop()
                    minimums.append((previous, adjusted))

                oldest = required - warehouse.stock
                while minimums and minimums[0][0] < oldest:
                    minimums.popleft()

                if minimums:
                    score = (
                        COUNT_WEIGHT
                        + warehouse.fixed_cost
                        + required * warehouse.unit_cost
                        + minimums[0][1]
                    )
                    current[required] = min(current[required], score)

        suffix_scores[index] = current

    return suffix_scores


def solve(input_text: str) -> str:
    quantity, warehouses = parse_input(input_text)
    suffix_scores = build_best_scores(warehouses, quantity)
    best_score = suffix_scores[0][quantity]
    if best_score == INFINITY:
        return "1"

    best_count, best_cost = divmod(best_score, COUNT_WEIGHT)
    allocations: list[tuple[Warehouse, int]] = []
    allocated_quantity = 0
    remaining_score = best_score

    for index, warehouse in enumerate(warehouses):
        remaining_quantity = quantity - allocated_quantity
        maximum_quantity = min(warehouse.stock, remaining_quantity)
        chosen_quantity = None

        for allocated in range(1, maximum_quantity + 1):
            rest = suffix_scores[index + 1][remaining_quantity - allocated]
            if rest == INFINITY:
                continue

            score = (
                COUNT_WEIGHT
                + warehouse.fixed_cost
                + allocated * warehouse.unit_cost
                + rest
            )
            if score == remaining_score:
                chosen_quantity = allocated
                break

        if chosen_quantity is None:
            continue

        allocations.append((warehouse, chosen_quantity))
        allocated_quantity += chosen_quantity
        remaining_score -= (
            COUNT_WEIGHT + warehouse.fixed_cost + chosen_quantity * warehouse.unit_cost
        )

    if allocated_quantity != quantity or remaining_score != 0:
        raise RuntimeError("failed to reconstruct a valid allocation")

    output = [f"{best_count} {best_cost}"]
    output.extend(
        f"{warehouse.warehouse_id} {allocated}" for warehouse, allocated in allocations
    )
    return "\n".join(output)


def main() -> int:
    try:
        result = solve(sys.stdin.read())
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
