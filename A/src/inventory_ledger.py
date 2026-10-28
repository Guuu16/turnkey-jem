"""Deterministic single-SKU inventory reservation ledger.

Input
-----
The first line contains the initial stock ``S`` and command count ``N``.
Each following line is one command:

    RESERVE event_id order_id qty
    RELEASE event_id order_id qty
    SHIP event_id order_id qty
    RESTOCK event_id qty

Rules
-----
* All quantities must be positive integers.
* Malformed commands are rejected without partial state changes.
* ``RESERVE`` succeeds only when available stock is sufficient.
* ``RELEASE`` and ``SHIP`` cannot exceed the order's current reservation.
* ``SHIP`` reduces both on-hand stock and the order's reservation.
* ``RESTOCK`` increases on-hand stock only.
* Every ``event_id`` is idempotent. Replaying a processed event returns
  ``DUPLICATE`` without changing state.
* An event rejected by a business rule is still considered processed.

Output
------
Each command prints ``STATUS on_hand reserved``. After all commands, the
program prints ``OPEN count`` followed by open reservations sorted by
``order_id``.

Constraints
-----------
``0 <= S <= 10**12``
``1 <= N <= 200_000``
``1 <= qty <= 10**12``
``event_id`` and ``order_id`` are non-empty ASCII tokens.
"""

from __future__ import annotations

import sys

MAX_AMOUNT = 10**12
MAX_COMMANDS = 200000


def is_ascii_token(token: str) -> bool:
    return bool(token) and all(33 <= ord(char) <= 126 for char in token)


class InventoryLedger:
    def __init__(self, initial_stock: int) -> None:
        self.on_hand = initial_stock
        self.reserved = 0
        self.orders: dict[str, int] = {}
        self.seen: set[str] = set()

    def execute(self, line: str) -> str:
        parts = line.split()
        if not parts:
            return "REJECTED"

        command = parts[0]
        if command == "RESTOCK":
            expected_size = 3
        elif command in {"RESERVE", "RELEASE", "SHIP"}:
            expected_size = 4
        else:
            return "REJECTED"

        if len(parts) != expected_size:
            return "REJECTED"

        event_id = parts[1]
        if event_id in self.seen:
            return "DUPLICATE"

        quantity = parse_quantity(parts[-1])
        if not is_ascii_token(event_id) or quantity is None:
            return "REJECTED"

        if command == "RESTOCK":
            self.seen.add(event_id)
            return self.restock(quantity)

        order_id = parts[2]
        if not is_ascii_token(order_id):
            return "REJECTED"

        self.seen.add(event_id)
        if command == "RESERVE":
            return self.reserve(order_id, quantity)
        if command == "RELEASE":
            return self.release_or_ship(order_id, quantity, reduce_on_hand=False)
        return self.release_or_ship(order_id, quantity, reduce_on_hand=True)

    def reserve(self, order_id: str, quantity: int) -> str:
        if quantity > self.on_hand - self.reserved:
            return "REJECTED"

        self.reserved += quantity
        self.orders[order_id] = self.orders.get(order_id, 0) + quantity
        return "OK"

    def release_or_ship(
        self, order_id: str, quantity: int, reduce_on_hand: bool
    ) -> str:
        order_reserved = self.orders.get(order_id, 0)
        if quantity > order_reserved:
            return "REJECTED"

        if reduce_on_hand:
            self.on_hand -= quantity

        remaining = order_reserved - quantity
        self.reserved -= quantity

        if remaining:
            self.orders[order_id] = remaining
        else:
            del self.orders[order_id]
        return "OK"

    def restock(self, quantity: int) -> str:
        self.on_hand += quantity
        return "OK"


def parse_header(line: str) -> tuple[int, int]:
    """Parse and validate the initial stock and command count."""
    parts = line.split()
    if len(parts) != 2 or not all(part.isascii() and part.isdigit() for part in parts):
        raise ValueError("invalid header")

    initial_stock, command_count = map(int, parts)
    if initial_stock > MAX_AMOUNT:
        raise ValueError("initial stock is too large")
    if not 1 <= command_count <= MAX_COMMANDS:
        raise ValueError("command count is out of range")

    return initial_stock, command_count


def parse_quantity(token: str) -> int | None:
    """Parse a positive quantity, returning None when it is invalid."""
    if not (token.isascii() and token.isdigit()):
        return None

    quantity = int(token)
    if not 1 <= quantity <= MAX_AMOUNT:
        return None

    return quantity


def process_ledger(input_text: str) -> str:
    lines = input_text.splitlines()
    if not lines:
        raise ValueError("missing header")

    initial_stock, command_count = parse_header(lines[0])
    commands = lines[1:]
    if len(commands) != command_count:
        raise ValueError("command count does not match header")

    ledger = InventoryLedger(initial_stock)
    output: list[str] = []

    for line in commands:
        status = ledger.execute(line)
        output.append(f"{status} {ledger.on_hand} {ledger.reserved}")

    open_orders = sorted(ledger.orders.items())
    output.append(f"OPEN {len(open_orders)}")
    output.extend(f"{order_id} {quantity}" for order_id, quantity in open_orders)
    return "\n".join(output)


def main() -> int:
    try:
        result = process_ledger(sys.stdin.read())
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
