"""#file_N# / #command_N# tokens in setUpCode and tearDownCode.

The testers pass the ``Solution`` enum as ``where``; the report keys are
``student_file_list`` etc., so the key must be built from the enum value.
"""

from __future__ import annotations

from testers.tests.test_base import Solution, apply_token_exchange_to_code  # type: ignore


def test_file_and_command_tokens_replaced_for_solution_enum():
    report = {
        "student_file_list": ["data.csv"],
        "student_command_list": ["myfunc"],
    }
    code = apply_token_exchange_to_code(
        ["load('#file_1#')", "#command_1#()"], report, Solution.student
    )
    assert code == ["load('data.csv')", "myfunc()"]


def test_plain_string_where_still_works():
    report = {"reference_file_list": ["ref.csv"]}
    assert apply_token_exchange_to_code(["#file_1#"], report, "reference") == ["ref.csv"]
