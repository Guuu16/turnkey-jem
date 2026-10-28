import random

import pytest
from fulfilment_cases import INVALID_CASES, NORMAL_CASES
from fulfilment_oracle import brute_force

from fulfilment import solve


@pytest.mark.parametrize(("input_text", "expected"), NORMAL_CASES)
def test_normal_input(input_text: str, expected: str) -> None:
    assert solve(input_text) == expected


@pytest.mark.parametrize(("input_text", "expected"), INVALID_CASES)
def test_invalid_input(input_text: str, expected: type[Exception]) -> None:
    with pytest.raises(expected):
        solve(input_text)


@pytest.mark.parametrize("seed", range(40))
def test_matches_brute_force_oracle(seed: int) -> None:
    randomizer = random.Random(seed)
    warehouse_count = randomizer.randint(1, 6)
    quantity = randomizer.randint(1, 12)
    ids = randomizer.sample(["A", "B", "C", "D", "E", "F"], warehouse_count)
    warehouses = [
        (
            warehouse_id,
            randomizer.randint(0, 4),
            randomizer.randint(0, 5),
            randomizer.randint(0, 5),
        )
        for warehouse_id in ids
    ]

    lines = [f"{warehouse_count} {quantity}"]
    for warehouse_id, stock, fixed_cost, unit_cost in warehouses:
        lines.append(f"{warehouse_id} {stock} {fixed_cost} {unit_cost}")

    assert solve("\n".join(lines)) == brute_force(warehouses, quantity)
