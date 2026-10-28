from __future__ import annotations


def brute_force(warehouses: list[tuple[str, int, int, int]], quantity: int) -> str:
    warehouses = sorted(warehouses)
    best: tuple[int, int, tuple[tuple[str, int], ...]] | None = None

    def search(
        index: int,
        remaining: int,
        count: int,
        cost: int,
        allocations: list[tuple[str, int]],
    ) -> None:
        nonlocal best

        if remaining == 0:
            candidate = (count, cost, tuple(allocations))
            if best is None or candidate < best:
                best = candidate
            return

        if index == len(warehouses):
            return

        warehouse_id, stock, fixed_cost, unit_cost = warehouses[index]
        for allocated in range(min(stock, remaining) + 1):
            if allocated:
                allocations.append((warehouse_id, allocated))
                search(
                    index + 1,
                    remaining - allocated,
                    count + 1,
                    cost + fixed_cost + allocated * unit_cost,
                    allocations,
                )
                allocations.pop()
            else:
                search(index + 1, remaining, count, cost, allocations)

    search(0, quantity, 0, 0, [])
    if best is None:
        return "1"

    count, cost, allocations = best
    lines = [f"{count} {cost}"]
    lines.extend(
        f"{warehouse_id} {allocated}" for warehouse_id, allocated in allocations
    )
    return "\n".join(lines)
