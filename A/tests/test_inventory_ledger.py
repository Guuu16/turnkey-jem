from collections.abc import Callable

import pytest
from inventory_cases import INVALID_CASES, NORMAL_CASES

from inventory_ledger import process_ledger

NormalExpected = str | Callable[[str], None]
InvalidExpected = str | type[Exception]


@pytest.mark.parametrize(("input_text", "expected"), NORMAL_CASES)
def test_normal_input(input_text: str, expected: NormalExpected) -> None:
    result = process_ledger(input_text)

    if callable(expected):
        expected(result)
    else:
        assert result == expected


@pytest.mark.parametrize(("input_text", "expected"), INVALID_CASES)
def test_invalid_input(input_text: str, expected: InvalidExpected) -> None:
    if isinstance(expected, type):
        with pytest.raises(expected):
            process_ledger(input_text)
        return

    assert process_ledger(input_text) == expected
