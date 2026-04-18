import pytest
from pipewarden.checks.custom_sql_check import CustomSQLCheck
from pipewarden.checks.base import CheckStatus


def make_executor(return_value):
    """Return a simple executor function that ignores the query and returns a fixed value."""
    def execute(query: str):
        return return_value
    return execute


def make_failing_executor(exc):
    def execute(query: str):
        raise exc
    return execute


@pytest.fixture
def default_check():
    return CustomSQLCheck(
        name="test_sql",
        query="SELECT COUNT(*) FROM orders",
        execute_fn=make_executor(100),
        min_value=50,
        max_value=200,
    )


def test_passes_within_range(default_check):
    result = default_check.run()
    assert result.status == CheckStatus.PASSED


def test_fails_below_minimum():
    check = CustomSQLCheck(
        name="low", query="SELECT 1", execute_fn=make_executor(10),
        min_value=50,
    )
    result = check.run()
    assert result.status == CheckStatus.FAILED
    assert "below minimum" in result.message


def test_fails_above_maximum():
    check = CustomSQLCheck(
        name="high", query="SELECT 1", execute_fn=make_executor(300),
        max_value=200,
    )
    result = check.run()
    assert result.status == CheckStatus.FAILED
    assert "above maximum" in result.message


def test_warning_thresholds():
    check = CustomSQLCheck(
        name="warn", query="SELECT 1", execute_fn=make_executor(45),
        min_value=10, warning_min=50,
    )
    result = check.run()
    assert result.status == CheckStatus.WARNING


def test_expected_value_match():
    check = CustomSQLCheck(
        name="exact", query="SELECT status", execute_fn=make_executor("ok"),
        expected_value="ok",
    )
    result = check.run()
    assert result.status == CheckStatus.PASSED


def test_expected_value_mismatch():
    check = CustomSQLCheck(
        name="exact", query="SELECT status", execute_fn=make_executor("error"),
        expected_value="ok",
    )
    result = check.run()
    assert result.status == CheckStatus.FAILED


def test_executor_exception():
    check = CustomSQLCheck(
        name="err", query="SELECT 1",
        execute_fn=make_failing_executor(RuntimeError("connection refused")),
    )
    result = check.run()
    assert result.status == CheckStatus.FAILED
    assert "connection refused" in result.message


def test_non_numeric_result_without_expected():
    check = CustomSQLCheck(
        name="non_num", query="SELECT 1", execute_fn=make_executor("text"),
        min_value=0,
    )
    result = check.run()
    assert result.status == CheckStatus.FAILED
    assert "not numeric" in result.message
