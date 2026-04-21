"""Public API for pipewarden checks.

This module exposes all built-in check classes and result utilities for
convenient top-level imports::

    from pipewarden.checks import NullCheck, RowCountCheck, passed, failed

Check classes
-------------
- CompletenessCheck   – fraction of non-null values meets a threshold
- CrossFieldCheck     – validates relationships between two columns
- CustomSQLCheck      – arbitrary SQL expression evaluated as a boolean
- DistributionCheck   – compares value distributions against a baseline
- DuplicateRowCheck   – detects duplicate rows across specified columns
- FreshnessCheck      – asserts data was updated within a time window
- NullCheck           – ensures a column contains no (or limited) nulls
- ReferentialIntegrityCheck – foreign-key style integrity between tables
- RegexCheck          – validates column values against a regex pattern
- RowCountCheck       – asserts row count falls within expected bounds
- SchemaCheck         – validates column names and/or data types
- StatisticalOutlierCheck – flags rows whose values are statistical outliers
- TrendCheck          – detects unexpected changes in a metric over time
- UniquenessCheck     – asserts that column values are unique
- ValueRangeCheck     – asserts column values fall within a numeric range

Result helpers
--------------
- passed / warned / failed  – convenience constructors for CheckResult
"""

from pipewarden.checks.base import CheckResult, CheckStatus, failed, passed, warned
from pipewarden.checks.completeness_check import CompletenessCheck
from pipewarden.checks.cross_field_check import CrossFieldCheck
from pipewarden.checks.custom_sql_check import CustomSQLCheck
from pipewarden.checks.distribution_check import DistributionCheck
from pipewarden.checks.duplicate_row_check import DuplicateRowCheck
from pipewarden.checks.freshness_check import FreshnessCheck
from pipewarden.checks.null_check import NullCheck
from pipewarden.checks.referential_integrity_check import ReferentialIntegrityCheck
from pipewarden.checks.regex_check import RegexCheck
from pipewarden.checks.row_count import RowCountCheck
from pipewarden.checks.schema_check import SchemaCheck
from pipewarden.checks.statistical_outlier_check import StatisticalOutlierCheck
from pipewarden.checks.trend_check import TrendCheck
from pipewarden.checks.uniqueness_check import UniquenessCheck
from pipewarden.checks.value_range_check import ValueRangeCheck

__all__ = [
    "CheckResult",
    "CheckStatus",
    "CompletenessCheck",
    "CrossFieldCheck",
    "CustomSQLCheck",
    "DistributionCheck",
    "DuplicateRowCheck",
    "FreshnessCheck",
    "NullCheck",
    "ReferentialIntegrityCheck",
    "RegexCheck",
    "RowCountCheck",
    "SchemaCheck",
    "StatisticalOutlierCheck",
    "TrendCheck",
    "UniquenessCheck",
    "ValueRangeCheck",
    "failed",
    "passed",
    "warned",
]
