"""
Computor Testing - Test Report Models

Models for test execution output (testSummary.json format).
These represent the output produced by computor-testing and consumed/stored
by computor-backend in Result.result_json.
"""

from typing import List, Optional
from pydantic import Field

from .testing import ComputorBase, StatusEnum, ResultEnum


class ComputorReportSummary(ComputorBase):
    """Test count statistics."""
    total: int = Field(ge=0, default=0)
    passed: int = Field(ge=0, default=0)
    failed: int = Field(ge=0, default=0)
    skipped: int = Field(ge=0, default=0)


class ComputorReportProperties(ComputorBase):
    """Common properties for test report entries."""
    timestamp: Optional[str] = Field(default=None)
    type: Optional[str] = Field(default=None)
    version: Optional[str] = Field(default=None)
    name: Optional[str] = Field(default=None)
    description: Optional[str] = Field(default=None)
    status: Optional[StatusEnum] = Field(default=None, validate_default=True)
    result: Optional[ResultEnum] = Field(default=None, validate_default=True)
    summary: Optional[ComputorReportSummary] = Field(default=None)
    statusMessage: Optional[str] = Field(default=None)
    resultMessage: Optional[str] = Field(default=None)
    details: Optional[str] = Field(default=None)
    setup: Optional[str] = Field(default=None)
    teardown: Optional[str] = Field(default=None)
    duration: Optional[float] = Field(default=None)
    executionDuration: Optional[float] = Field(default=None)
    environment: Optional[dict] = Field(default=None)
    properties: Optional[dict] = Field(default=None)
    debug: Optional[dict] = Field(default=None)


class ComputorReportSub(ComputorReportProperties):
    """Individual test result within a test collection."""
    pass


class ComputorReportMain(ComputorReportProperties):
    """Test collection result containing individual test results."""
    tests: Optional[List[ComputorReportSub]] = Field(default=None)


class ComputorReport(ComputorReportProperties):
    """Top-level test report containing test collection results."""
    tests: Optional[List[ComputorReportMain]] = Field(default=None)
