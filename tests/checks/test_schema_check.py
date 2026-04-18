import pytest
from pipewarden.checks.schema_check import SchemaCheck
from pipewarden.checks.base import CheckStatus


@pytest.fixture
def default_check():
    return SchemaCheck(required_columns=["id", "name", "email"])


def make_rows(keys, values_list):
    return [dict(zip(keys, vals)) for vals in values_list]


def test_passes_with_exact_columns(default_check):
    rows = make_rows(["id", "name", "email"], [(1, "Alice", "a@example.com")])
    result = default_check.run(rows)
    assert result.status == CheckStatus.PASSED


def test_passes_with_extra_columns_allowed(default_check):
    rows = make_rows(["id", "name", "email", "age"], [(1, "Alice", "a@b.com", 30)])
    result = default_check.run(rows)
    assert result.status == CheckStatus.PASSED
    assert "extra" in result.message


def test_fails_with_extra_columns_disallowed():
    check = SchemaCheck(required_columns=["id", "name"], allow_extra_columns=False)
    rows = make_rows(["id", "name", "extra"], [(1, "Alice", "oops")])
    result = check.run(rows)
    assert result.status == CheckStatus.FAILED
    assert "extra_columns" in result.details


def test_fails_missing_columns(default_check):
    rows = make_rows(["id", "name"], [(1, "Alice")])
    result = default_check.run(rows)
    assert result.status == CheckStatus.FAILED
    assert "email" in result.details["missing_columns"]


def test_fails_type_mismatch():
    check = SchemaCheck(
        required_columns=["id", "score"],
        type_map={"id": int, "score": float},
    )
    rows = [{"id": "not-an-int", "score": 9.5}]
    result = check.run(rows)
    assert result.status == CheckStatus.FAILED
    assert result.details["type_errors"][0]["column"] == "id"


def test_passes_type_check():
    check = SchemaCheck(
        required_columns=["id", "score"],
        type_map={"id": int, "score": float},
    )
    rows = [{"id": 1, "score": 9.5}]
    result = check.run(rows)
    assert result.status == CheckStatus.PASSED


def test_fails_empty_rows(default_check):
    result = default_check.run([])
    assert result.status == CheckStatus.FAILED
    assert "No rows" in result.message


def test_to_dict(default_check):
    rows = make_rows(["id", "name", "email"], [(1, "Bob", "b@b.com")])
    result = default_check.run(rows)
    d = result.to_dict()
    assert d["check"] == "schema_check"
    assert d["status"] == "passed"
