"""Alternative fulfilment solver using a 2D cost DP and min-heap."""

from __future__ import annotations

import sys
from heapq import heappop, heappush

from fulfilment import INFINITY, Warehouse, parse_input


def build_suffix_costs(
    warehouses: list[Warehouse],
    quantity: int,
) -> list[list[list[int]]]:
    warehouse_count = len(warehouses)
    suffix_costs: list[list[list[int]]] = [[] for _ in range(warehouse_count + 1)]

    base = [[INFINITY] * (quantity + 1) for _ in range(warehouse_count + 1)]
    base[0][0] = 0
    suffix_costs[warehouse_count] = base

    for index in range(warehouse_count - 1, -1, -1):
        warehouse = warehouses[index]
        following = suffix_costs[index + 1]
        current = [row[:] for row in following]

        if warehouse.stock == 0:
            suffix_costs[index] = current
            continue

        for used_count in range(warehouse_count):
            source = following[used_count]
            target = current[used_count + 1]
            candidates: list[tuple[int, int]] = []

            for required in range(1, quantity + 1):
                previous = required - 1
                if source[previous] < INFINITY:
                    adjusted = source[previous] - previous * warehouse.unit_cost
                    heappush(candidates, (adjusted, previous))

                oldest = required - warehouse.stock
                while candidates and candidates[0][1] < oldest:
                    heappop(candidates)

                if candidates:
                    cost = (
                        warehouse.fixed_cost
                        + required * warehouse.unit_cost
                        + candidates[0][0]
                    )
                    target[required] = min(target[required], cost)

        suffix_costs[index] = current

    return suffix_costs


def solve(input_text: str) -> str:
    quantity, warehouses = parse_input(input_text)
    suffix_costs = build_suffix_costs(warehouses, quantity)
    best_count = next(
        (
            used_count
            for used_count, costs in enumerate(suffix_costs[0])
            if costs[quantity] < INFINITY
        ),
        None,
    )
    if best_count is None:
        return "1"

    best_cost = suffix_costs[0][best_count][quantity]
    allocations: list[tuple[Warehouse, int]] = []
    used_count = 0
    allocated_quantity = 0
    spent_cost = 0

    for index, warehouse in enumerate(warehouses):
        remaining_count = best_count - used_count
        remaining_quantity = quantity - allocated_quantity
        maximum_quantity = min(warehouse.stock, remaining_quantity)
        chosen_quantity = None

        if remaining_count > 0:
            for allocated in range(1, maximum_quantity + 1):
                rest = suffix_costs[index + 1][remaining_count - 1][
                    remaining_quantity - allocated
                ]
                if rest == INFINITY:
                    continue

                cost = warehouse.fixed_cost + allocated * warehouse.unit_cost + rest
                if cost == best_cost - spent_cost:
                    chosen_quantity = allocated
                    break

        if chosen_quantity is None:
            continue

        allocations.append((warehouse, chosen_quantity))
        used_count += 1
        allocated_quantity += chosen_quantity
        spent_cost += warehouse.fixed_cost + chosen_quantity * warehouse.unit_cost

    if (
        used_count != best_count
        or allocated_quantity != quantity
        or spent_cost != best_cost
    ):
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
