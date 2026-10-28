import pytest

from inventory_ledger import MAX_AMOUNT, MAX_COMMANDS


def make_input(stock: int, *commands: str) -> str:
    return f"{stock} {len(commands)}\n" + "\n".join(commands)


def assert_maximum_command_case(output: str) -> None:
    lines = output.splitlines()

    assert len(lines) == MAX_COMMANDS + 1
    assert lines[0] == "OK 1 0"
    assert lines[-2] == f"OK {MAX_COMMANDS} 0"
    assert lines[-1] == "OPEN 0"


MAX_COMMANDS_INPUT = (
    f"0 {MAX_COMMANDS}\n"
    + "\n".join(f"RESTOCK e{index} 1" for index in range(MAX_COMMANDS))
    + "\n"
)


# Keep expected outputs vertically aligned for easier review.
# fmt: off
INVALID_CASES = [
    # Header structure and numeric format.
    pytest.param("", ValueError, id="header-missing-input"),
    pytest.param("5", ValueError, id="header-one-field"),
    pytest.param("5 1 2", ValueError, id="header-three-fields"),
    pytest.param(
        "abc 1\nRESTOCK e1 1\n", ValueError, id="header-non-decimal-stock"
    ),
    pytest.param(
        "5 abc\nRESTOCK e1 1\n", ValueError, id="header-non-decimal-count"
    ),
    pytest.param(
        "１ 1\nRESTOCK e1 1\n", ValueError, id="header-non-ascii-stock"
    ),
    pytest.param(
        "-1 1\nRESTOCK e1 1\n",
        ValueError,
        id="header-negative-stock",
    ),
    pytest.param(
        f"{MAX_AMOUNT + 1} 1\nRESTOCK e1 1\n",
        ValueError,
        id="header-stock-above-limit",
    ),
    pytest.param("0 0\n", ValueError, id="header-command-count-zero"),
    pytest.param(
        "0 -1\n",
        ValueError,
        id="header-command-count-negative",
    ),
    pytest.param(
        f"0 {MAX_COMMANDS + 1}\n",
        ValueError,
        id="header-command-count-above-limit",
    ),
    pytest.param(
        "5 2\nRESTOCK e1 1\n",
        ValueError,
        id="header-command-count-too-few",
    ),
    pytest.param(
        "5 1\nRESTOCK e1 1\nRESTOCK e2 1\n",
        ValueError,
        id="header-command-count-too-many",
    ),
    # Command syntax.
    pytest.param(
        "5 1\n\n",
        "REJECTED 5 0\nOPEN 0",
        id="format-empty-command",
    ),
    pytest.param(
        make_input(
            5,
            "BOGUS e1",
            "reserve e1 o1 1",
            "RESERVE e1 o1",
            "RESERVE e1 o1 1 extra",
            "RESTOCK e1",
            "RESTOCK e1 1 extra",
        ),
        (
            "REJECTED 5 0\n"
            "REJECTED 5 0\n"
            "REJECTED 5 0\n"
            "REJECTED 5 0\n"
            "REJECTED 5 0\n"
            "REJECTED 5 0\n"
            "OPEN 0"
        ),
        id="format-unknown-lowercase-and-arity",
    ),
    # Invalid event_id and order_id tokens.
    pytest.param(
        make_input(
            5,
            "RESERVE \u00e9 o1 1",
            "RESERVE \U0001f600 o1 1",
            "RESERVE e1 \u00e9 1",
            "RESERVE e1 \U0001f600 1",
        ),
        (
            "REJECTED 5 0\n"
            "REJECTED 5 0\n"
            "REJECTED 5 0\n"
            "REJECTED 5 0\n"
            "OPEN 0"
        ),
        id="token-non-ascii-ids",
    ),
    pytest.param(
        make_input(
            5,
            "RESERVE  o1 1",
            "RESERVE e1  1",
        ),
        "REJECTED 5 0\nREJECTED 5 0\nOPEN 0",
        id="token-empty-ids",
    ),
    pytest.param(
        make_input(5, "RESERVE \x7f o1 1"),
        "REJECTED 5 0\nOPEN 0",
        id="token-ascii-control",
    ),
    # Invalid quantities.
    pytest.param(
        make_input(5, "RESERVE e1 o1 0"),
        "REJECTED 5 0\nOPEN 0",
        id="quantity-zero",
    ),
    pytest.param(
        make_input(5, "RESERVE e1 o1 -1"),
        "REJECTED 5 0\nOPEN 0",
        id="quantity-negative",
    ),
    pytest.param(
        make_input(5, "RESERVE e1 o1 1.5"),
        "REJECTED 5 0\nOPEN 0",
        id="quantity-decimal",
    ),
    pytest.param(
        make_input(5, "RESERVE e1 o1 abc"),
        "REJECTED 5 0\nOPEN 0",
        id="quantity-non-numeric",
    ),
    pytest.param(
        make_input(5, "RESERVE e1 o1 1e3"),
        "REJECTED 5 0\nOPEN 0",
        id="quantity-scientific-notation",
    ),
    pytest.param(
        make_input(5, f"RESERVE e1 o1 {MAX_AMOUNT + 1}"),
        "REJECTED 5 0\nOPEN 0",
        id="quantity-above-limit",
    ),
    pytest.param(
        make_input(5, "RESERVE e1 o1 １"),
        "REJECTED 5 0\nOPEN 0",
        id="quantity-non-ascii",
    ),
    pytest.param(
        make_input(
            0,
            f"RESTOCK e1 {MAX_AMOUNT + 1}",
            "RESTOCK e1 1",
        ),
        "REJECTED 0 0\nOK 1 0\nOPEN 0",
        id="quantity-above-limit-does-not-consume-event",
    ),
    # Malformed commands must not consume an event ID.
    pytest.param(
        make_input(
            5,
            "RESERVE e1 o1 0",
            "RESERVE e1 o1 abc",
            "RESERVE e1 \u00e9 1",
            "RESERVE e1 o1",
            "BOGUS e1",
            "RESERVE e1 o1 1",
        ),
        (
            "REJECTED 5 0\n"
            "REJECTED 5 0\n"
            "REJECTED 5 0\n"
            "REJECTED 5 0\n"
            "REJECTED 5 0\n"
            "OK 5 1\n"
            "OPEN 1\n"
            "o1 1"
        ),
        id="idempotency-malformed-input-does-not-consume-event",
    ),
]


NORMAL_CASES = [
    # Specification example.
    pytest.param(
        make_input(
            10,
            "RESERVE e1 o100 4",
            "RESERVE e2 o200 7",
            "SHIP e3 o100 2",
            "RELEASE e4 o100 2",
            "RESTOCK e5 3",
            "RESERVE e2 o999 1",
        ),
        (
            "OK 10 4\n"
            "REJECTED 10 4\n"
            "OK 8 2\n"
            "OK 8 0\n"
            "OK 11 0\n"
            "DUPLICATE 11 0\n"
            "OPEN 0"
        ),
        id="specification-example",
    ),
    # Header and quantity boundaries.
    pytest.param(
        make_input(0, "RESTOCK e1 1"),
        "OK 1 0\nOPEN 0",
        id="constraint-zero-stock-and-minimum-command-count",
    ),
    pytest.param(
        make_input(MAX_AMOUNT, f"RESERVE e1 o1 {MAX_AMOUNT}"),
        f"OK {MAX_AMOUNT} {MAX_AMOUNT}\nOPEN 1\no1 {MAX_AMOUNT}",
        id="constraint-max-stock-and-quantity",
    ),
    pytest.param(
        MAX_COMMANDS_INPUT,
        assert_maximum_command_case,
        id="constraint-maximum-command-count",
    ),
    # event_id and order_id token rules.
    pytest.param(
        make_input(
            5,
            "RESTOCK event-1 2",
            "RESERVE e.2 order#3 1",
        ),
        "OK 7 0\nOK 7 1\nOPEN 1\norder#3 1",
        id="token-valid-ascii-punctuation",
    ),
    pytest.param(
        make_input(5, "RESERVE ! ~ 1"),
        "OK 5 1\nOPEN 1\n~ 1",
        id="token-ascii-minimum-and-maximum",
    ),
    # Quantity constraints and malformed quantities.
    pytest.param(
        make_input(
            0,
            "RESTOCK e1 1",
            f"RESTOCK e2 {MAX_AMOUNT}",
        ),
        f"OK 1 0\nOK {MAX_AMOUNT + 1} 0\nOPEN 0",
        id="quantity-minimum-and-maximum",
    ),
    # RESERVE rules.
    pytest.param(
        make_input(
            10,
            "RESERVE e1 o1 4",
            "RESERVE e2 o2 6",
            "RESERVE e3 o3 1",
        ),
        (
            "OK 10 4\n"
            "OK 10 10\n"
            "REJECTED 10 10\n"
            "OPEN 2\n"
            "o1 4\n"
            "o2 6"
        ),
        id="reserve-available-stock-boundary",
    ),
    pytest.param(
        make_input(
            10,
            "RESERVE e1 o1 2",
            "RESERVE e2 o1 3",
        ),
        "OK 10 2\nOK 10 5\nOPEN 1\no1 5",
        id="reserve-accumulates-same-order",
    ),
    pytest.param(
        make_input(0, "RESERVE e1 o1 1"),
        "REJECTED 0 0\nOPEN 0",
        id="reserve-zero-stock",
    ),
    pytest.param(
        make_input(5, "RESERVE e1 o1 0002"),
        "OK 5 2\nOPEN 1\no1 2",
        id="reserve-leading-zeroes",
    ),
    # RELEASE rules.
    pytest.param(
        make_input(
            10,
            "RESERVE e1 o1 6",
            "RESERVE e2 o2 3",
            "RELEASE e3 o1 2",
            "RELEASE e4 o1 5",
            "RELEASE e5 o2 3",
            "RELEASE e6 o1 4",
        ),
        (
            "OK 10 6\n"
            "OK 10 9\n"
            "OK 10 7\n"
            "REJECTED 10 7\n"
            "OK 10 4\n"
            "OK 10 0\n"
            "OPEN 0"
        ),
        id="release-partial-exact-over-and-cross-order",
    ),
    pytest.param(
        make_input(
            5,
            "RESERVE e1 o1 2",
            "RELEASE e2 missing 1",
        ),
        "OK 5 2\nREJECTED 5 2\nOPEN 1\no1 2",
        id="release-unknown-order",
    ),
    # SHIP rules.
    pytest.param(
        make_input(
            10,
            "RESERVE e1 o1 6",
            "RESERVE e2 o2 3",
            "SHIP e3 o1 2",
            "SHIP e4 o1 5",
            "SHIP e5 o2 3",
            "SHIP e6 o1 4",
        ),
        (
            "OK 10 6\n"
            "OK 10 9\n"
            "OK 8 7\n"
            "REJECTED 8 7\n"
            "OK 5 4\n"
            "OK 1 0\n"
            "OPEN 0"
        ),
        id="ship-partial-exact-over-and-cross-order",
    ),
    pytest.param(
        make_input(
            5,
            "RESERVE e1 o1 2",
            "SHIP e2 missing 1",
        ),
        "OK 5 2\nREJECTED 5 2\nOPEN 1\no1 2",
        id="ship-unknown-order",
    ),
    # RESTOCK rules.
    pytest.param(
        make_input(
            5,
            "RESERVE e1 o1 5",
            "RESTOCK e2 3",
        ),
        "OK 5 5\nOK 8 5\nOPEN 1\no1 5",
        id="restock-keeps-reservations",
    ),
    pytest.param(
        make_input(
            0,
            "RESTOCK e1 5",
            "RESERVE e2 o1 5",
        ),
        "OK 5 0\nOK 5 5\nOPEN 1\no1 5",
        id="restock-enables-later-reserve",
    ),
    # event_id idempotency.
    pytest.param(
        make_input(
            10,
            "RESTOCK e1 5",
            "RESTOCK e1 1",
            "RESERVE e2 o1 4",
            "RESERVE e2 o2 9",
            "SHIP e3 o1 2",
            "SHIP e3 o2 99",
            "RELEASE e4 o1 1",
            "RELEASE e4 o1 99",
        ),
        (
            "OK 15 0\n"
            "DUPLICATE 15 0\n"
            "OK 15 4\n"
            "DUPLICATE 15 4\n"
            "OK 13 2\n"
            "DUPLICATE 13 2\n"
            "OK 13 1\n"
            "DUPLICATE 13 1\n"
            "OPEN 1\n"
            "o1 1"
        ),
        id="idempotency-all-command-types",
    ),
    pytest.param(
        "0 2\nRESERVE e1 o1 1\nRESERVE e1 o1 1\n",
        "REJECTED 0 0\nDUPLICATE 0 0\nOPEN 0",
        id="idempotency-rejected-reserve-consumes-event",
    ),
    pytest.param(
        "5 2\nRELEASE e1 o1 1\nRESTOCK e1 1\n",
        "REJECTED 5 0\nDUPLICATE 5 0\nOPEN 0",
        id="idempotency-rejected-release-consumes-event",
    ),
    pytest.param(
        "5 2\nSHIP e1 o1 1\nRESTOCK e1 1\n",
        "REJECTED 5 0\nDUPLICATE 5 0\nOPEN 0",
        id="idempotency-rejected-ship-consumes-event",
    ),
    # OPEN output rules.
    pytest.param(
        make_input(5, "RESTOCK e1 1"),
        "OK 6 0\nOPEN 0",
        id="output-open-zero",
    ),
    pytest.param(
        make_input(
            20,
            "RESERVE e1 o2 5",
            "RESERVE e2 o1 3",
            "RESERVE e3 o3 2",
            "RELEASE e4 o2 2",
        ),
        (
            "OK 20 5\n"
            "OK 20 8\n"
            "OK 20 10\n"
            "OK 20 8\n"
            "OPEN 3\n"
            "o1 3\n"
            "o2 3\n"
            "o3 2"
        ),
        id="output-open-orders-sorted",
    ),
    pytest.param(
        make_input(
            10,
            "RESERVE e1 o1 3",
            "RELEASE e2 o1 3",
            "RESERVE e3 o2 2",
            "SHIP e4 o2 2",
        ),
        "OK 10 3\nOK 10 0\nOK 10 2\nOK 8 0\nOPEN 0",
        id="output-closed-orders-removed",
    ),
]
# fmt: on
