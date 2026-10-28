import pytest


def make_input(quantity: int, *warehouses: str) -> str:
    return f"{len(warehouses)} {quantity}\n" + "\n".join(warehouses)


ONE_LARGE_WAREHOUSE = make_input(
    2000,
    *(f"W{index:02d} 2000 {index} {index}" for index in range(30)),
)

MANY_REQUIRED_WAREHOUSES = make_input(
    2000,
    *(f"W{index:02d} 67 0 1" for index in range(30)),
)

MANY_REQUIRED_OUTPUT = "30 2000\nW00 57\n" + "\n".join(
    f"W{index:02d} 67" for index in range(1, 30)
)


NORMAL_CASES = [
    pytest.param(
        make_input(
            7,
            "AU 5 8 2",
            "CN 7 20 1",
            "US 4 3 4",
        ),
        "1 27\nCN 7",
        id="specification-example",
    ),
    pytest.param(
        make_input(8, "A 3 0 1", "B 4 0 1"),
        "1",
        id="impossible-order",
    ),
    pytest.param(
        make_input(5, "A 5 10 2"),
        "1 20\nA 5",
        id="exact-fulfilment",
    ),
    pytest.param(
        make_input(
            3,
            "A 0 0 0",
            "B 2 5 1",
            "C 5 10 0",
        ),
        "1 10\nC 3",
        id="zero-stock-warehouse",
    ),
    pytest.param(
        make_input(
            5,
            "A 5 100 100",
            "B 3 1 1",
            "C 3 1 1",
        ),
        "1 600\nA 5",
        id="warehouse-count-precedes-cost",
    ),
    pytest.param(
        make_input(5, "A 5 100 0", "B 5 1 10"),
        "1 51\nB 5",
        id="fixed-cost-tradeoff",
    ),
    pytest.param(
        make_input(5, "A 5 0 5", "B 5 0 2"),
        "1 10\nB 5",
        id="unit-cost-tradeoff",
    ),
    pytest.param(
        make_input(
            2,
            "B 1 0 1",
            "A 1 0 1",
            "C 1 0 1",
        ),
        "2 2\nA 1\nB 1",
        id="equal-cost-lexicographic-warehouse-set",
    ),
    pytest.param(
        make_input(3, "B 2 0 1", "A 2 0 1"),
        "2 3\nA 1\nB 2",
        id="equal-cost-lexicographic-quantity",
    ),
    pytest.param(
        ONE_LARGE_WAREHOUSE,
        "1 0\nW00 2000",
        id="large-quantity-one-warehouse",
    ),
    pytest.param(
        MANY_REQUIRED_WAREHOUSES,
        MANY_REQUIRED_OUTPUT,
        id="large-quantity-many-warehouses",
    ),
]


INVALID_CASES = [
    pytest.param("", ValueError, id="missing-input"),
    pytest.param("2\nA 1 0 0\nB 1 0 0\n", ValueError, id="header-one-field"),
    pytest.param(
        "2 1 extra\nA 1 0 0\nB 1 0 0\n",
        ValueError,
        id="header-three-fields",
    ),
    pytest.param("0 1\n", ValueError, id="warehouse-count-zero"),
    pytest.param("31 1\n", ValueError, id="warehouse-count-above-limit"),
    pytest.param("1 -1\nA 1 0 0\n", ValueError, id="quantity-negative"),
    pytest.param("1 0\nA 1 0 0\n", ValueError, id="quantity-zero"),
    pytest.param("1 2001\nA 1 0 0\n", ValueError, id="quantity-above-limit"),
    pytest.param("2 1\nA 1 0 0\n", ValueError, id="missing-warehouse-row"),
    pytest.param(
        "1 1\nA 1 0 0\nB 1 0 0\n",
        ValueError,
        id="extra-warehouse-row",
    ),
    pytest.param("1 1\nA 1 0\n", ValueError, id="warehouse-three-fields"),
    pytest.param(
        "1 1\nA 1 0 0 extra\n",
        ValueError,
        id="warehouse-five-fields",
    ),
    pytest.param("1 1\nA x 0 0\n", ValueError, id="stock-non-numeric"),
    pytest.param("1 1\nA 1 x 0\n", ValueError, id="fixed-cost-non-numeric"),
    pytest.param("1 1\nA 1 0 x\n", ValueError, id="unit-cost-non-numeric"),
    pytest.param("1 1\nA -1 0 0\n", ValueError, id="stock-negative"),
    pytest.param("1 1\nA 2001 0 0\n", ValueError, id="stock-above-limit"),
    pytest.param("1 1\nA 1 -1 0\n", ValueError, id="fixed-cost-negative"),
    pytest.param("1 1\nA 1 0 -1\n", ValueError, id="unit-cost-negative"),
    pytest.param(
        "1 1\nA 1 1000001 0\n",
        ValueError,
        id="fixed-cost-above-limit",
    ),
    pytest.param(
        "1 1\nA 1 0 1000001\n",
        ValueError,
        id="unit-cost-above-limit",
    ),
    pytest.param(
        "2 1\nA 1 0 0\nA 1 0 0\n",
        ValueError,
        id="duplicate-warehouse-id",
    ),
    pytest.param("1 1\n\u00e9 1 0 0\n", ValueError, id="non-ascii-id"),
]
