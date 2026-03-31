"""
Computor Testing - Shared Test Specification Models

Language-agnostic data models for test definitions (test.yaml format).
These models are the single source of truth shared between computor-testing
(which executes tests) and computor-backend (which stores/displays them).

Note: Meta.yaml models live in codeability_meta.py (CodeAbilityMeta et al.).
"""

from enum import Enum
from typing import Any, List, Optional
from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator

from .codeability_meta import VERSION_REGEX


def empty_list_to_none(v):
    """Convert empty lists to None (MATLAB/R use [] for empty/null)."""
    if isinstance(v, list) and len(v) == 0:
        return None
    return v


def empty_string_to_none(v):
    """Convert empty strings to None (MATLAB uses '' for empty/null)."""
    if isinstance(v, str) and len(v) == 0:
        return None
    return v


DIRECTORIES = [
    "studentDirectory",
    "referenceDirectory",
    "testDirectory",
    "outputDirectory",
    "artifactDirectory",
]


class QualificationEnum(str, Enum):
    """Qualification types for test comparisons."""
    verifyEqual = "verifyEqual"
    matches = "matches"
    contains = "contains"
    startsWith = "startsWith"
    endsWith = "endsWith"
    count = "count"
    regexp = "regexp"
    # Extended qualifications for stdio testing
    matchesLine = "matchesLine"
    containsLine = "containsLine"
    lineCount = "lineCount"
    regexpMultiline = "regexpMultiline"
    numericOutput = "numericOutput"
    exitCode = "exitCode"


class TypeEnum(str, Enum):
    """Test types supported by the framework."""
    variable = "variable"
    graphics = "graphics"
    structural = "structural"
    linting = "linting"
    exist = "exist"
    error = "error"
    warning = "warning"
    help = "help"
    stdout = "stdout"
    # Extended types for compiled languages
    stderr = "stderr"
    stdio = "stdio"
    exitcode = "exitcode"
    compile = "compile"
    runtime = "runtime"
    # Document/text analysis types
    wordcount = "wordcount"
    paragraphcount = "paragraphcount"
    section = "section"
    linkcount = "linkcount"
    keyword = "keyword"
    uniquewords = "uniquewords"
    linecount = "linecount"
    charcount = "charcount"
    sentencecount = "sentencecount"
    headingcount = "headingcount"
    imagecount = "imagecount"
    codeblockcount = "codeblockcount"
    listitemcount = "listitemcount"
    pattern = "pattern"


class StatusEnum(str, Enum):
    """Test execution status."""
    scheduled = "SCHEDULED"
    completed = "COMPLETED"
    timedout = "TIMEDOUT"
    crashed = "CRASHED"
    cancelled = "CANCELLED"
    skipped = "SKIPPED"
    failed = "FAILED"


class ResultEnum(str, Enum):
    """Test result outcome."""
    passed = "PASSED"
    failed = "FAILED"
    skipped = "SKIPPED"


# Default values - can be overridden by language-specific implementations
DEFAULTS = {
    "specification": {
        "executionDirectory": None,
        "studentDirectory": "student",
        "referenceDirectory": "reference",
        "testDirectory": "testprograms",
        "outputDirectory": "output",
        "artifactDirectory": "artifacts",
        "testVersion": "v1",
        "storeGraphicsArtifacts": None,
        "outputName": "testSummary.json",
        "isLocalUsage": False,
    },
    "testsuite": {
        "type": "generic",
        "name": "Test Suite",
        "description": "Checks subtests and graphics",
        "version": "1.0",
    },
    "properties": {
        "qualification": QualificationEnum.verifyEqual,
        "failureMessage": "Some or all tests failed",
        "successMessage": "Congratulations! All tests passed",
        "relativeTolerance": 1.0e-12,
        "absoluteTolerance": 0.0001,
        "timeout": 180.0,
        "allowedOccuranceRange": [0, 0],
        "occuranceType": "NAME",
        "typeCheck": True,
        "shapeCheck": True,
        "equalNaN": True,
        "ignoreClass": False,
    },
    "meta": {
        "version": "1.0",
        "title": "TITLE",
        "description": "DESCRIPTION",
        "license": "Not specified",
    },
    "person": {
        "name": "unknown",
        "email": "unknown@tugraz.at",
        "affiliation": "TU Graz",
    },
}


class ComputorBase(BaseModel):
    """Base model for test specification models (strict: extra fields forbidden)."""
    model_config = ConfigDict(
        extra="forbid",
        use_enum_values=True,
        validate_assignment=True,
        coerce_numbers_to_str=True
    )


class ComputorTestCommon(BaseModel):
    """Common properties for all test types."""
    failureMessage: Optional[str] = Field(min_length=1, default=None)
    successMessage: Optional[str] = Field(min_length=1, default=None)
    qualification: Optional[QualificationEnum] = Field(default=None, validate_default=True)
    relativeTolerance: Optional[float] = Field(gt=0, default=None)
    absoluteTolerance: Optional[float] = Field(ge=0, default=None)
    allowedOccuranceRange: Optional[List[int]] = Field(
        min_length=2, max_length=2, default=None,
        validation_alias=AliasChoices('allowedOccuranceRange', 'allowedOccurrenceRange'),
    )
    occuranceType: Optional[str] = Field(
        min_length=1, default=None,
        validation_alias=AliasChoices('occuranceType', 'occurrenceType'),
    )
    typeCheck: Optional[bool] = Field(default=None)
    shapeCheck: Optional[bool] = Field(default=None)
    equalNaN: Optional[bool] = Field(default=None)
    ignoreClass: Optional[bool] = Field(default=None)
    verbosity: Optional[int] = Field(ge=0, le=3, default=None)

    @field_validator('relativeTolerance', 'absoluteTolerance', mode='before')
    @classmethod
    def empty_list_to_none_float(cls, v):
        return empty_list_to_none(v)

    @field_validator('allowedOccuranceRange', mode='before')
    @classmethod
    def empty_list_to_none_occurance_range(cls, v):
        if isinstance(v, list) and len(v) == 0:
            return None
        return v


class ComputorTestCollectionCommon(ComputorTestCommon):
    """Common properties for test collections."""
    storeGraphicsArtifacts: Optional[bool] = Field(default=None)
    competency: Optional[str] = Field(min_length=1, default=None)
    timeout: Optional[float] = Field(ge=0, default=None)


class ComputorTest(ComputorBase, ComputorTestCommon):
    """Individual test case definition."""
    name: str = Field(min_length=1)
    value: Optional[Any] = Field(default=None)
    evalString: Optional[str] = Field(min_length=1, default=None)
    pattern: Optional[str] = Field(min_length=1, default=None)
    countRequirement: Optional[int] = Field(ge=0, default=None)
    # Extended fields for stdio testing
    stdin: Optional[str | List[str]] = Field(default=None)
    expectedStdout: Optional[str | List[str]] = Field(default=None)
    expectedStderr: Optional[str | List[str]] = Field(default=None)
    expectedExitCode: Optional[int] = Field(default=None)
    lineNumber: Optional[int | List[int]] = Field(default=None)
    ignoreWhitespace: Optional[bool] = Field(default=None)
    ignoreCase: Optional[bool] = Field(default=None)
    trimOutput: Optional[bool] = Field(default=None)
    normalizeNewlines: Optional[bool] = Field(default=None)
    numericTolerance: Optional[float] = Field(ge=0, default=None)
    allowEmpty: Optional[bool] = Field(default=False)


class ComputorTestCollection(ComputorBase, ComputorTestCollectionCommon):
    """Test collection (group of related tests)."""
    type: Optional[TypeEnum] = Field(default=TypeEnum.variable, validate_default=True)
    name: str = Field(min_length=1)
    description: Optional[str] = Field(min_length=1, default=None)
    successDependency: Optional[str | int | List[str | int]] = Field(default=None)
    setUpCodeDependency: Optional[str] = Field(min_length=1, default=None)
    entryPoint: Optional[str] = Field(min_length=1, default=None)
    inputAnswers: Optional[str | List[str]] = Field(default=None)
    setUpCode: Optional[str | List[str]] = Field(default=None)
    tearDownCode: Optional[str | List[str]] = Field(default=None)
    id: Optional[str] = Field(min_length=1, default=None)
    file: Optional[str] = Field(min_length=1, default=None)
    tests: List[ComputorTest]
    # Extended fields for compiled languages
    compiler: Optional[str] = Field(default=None)
    compilerFlags: Optional[List[str]] = Field(default=None)
    linkerFlags: Optional[List[str]] = Field(default=None)
    sourceFiles: Optional[List[str]] = Field(default=None)
    executableName: Optional[str] = Field(default=None)
    workingDirectory: Optional[str] = Field(default=None)
    environment: Optional[dict] = Field(default=None)
    memoryLimit: Optional[int] = Field(ge=0, default=None)
    args: Optional[List[str]] = Field(default=None)

    @field_validator('setUpCodeDependency', 'entryPoint', 'id', 'file', 'description', mode='before')
    @classmethod
    def empty_str_to_none(cls, v):
        return empty_string_to_none(v)


class ComputorTestProperty(ComputorBase, ComputorTestCollectionCommon):
    """Test suite properties with defaults."""
    qualification: Optional[QualificationEnum] = Field(
        default=DEFAULTS["properties"]["qualification"], validate_default=True
    )
    resultMessage: Optional[str] = Field(default=None)
    failureMessage: Optional[str] = Field(
        min_length=1, default=DEFAULTS["properties"]["failureMessage"]
    )
    successMessage: Optional[str] = Field(
        min_length=1, default=DEFAULTS["properties"]["successMessage"]
    )
    relativeTolerance: Optional[float] = Field(
        gt=0, default=DEFAULTS["properties"]["relativeTolerance"]
    )
    absoluteTolerance: Optional[float] = Field(
        ge=0, default=DEFAULTS["properties"]["absoluteTolerance"]
    )
    allowedOccuranceRange: Optional[List[int]] = Field(
        min_length=2, max_length=2, default=DEFAULTS["properties"]["allowedOccuranceRange"],
        validation_alias=AliasChoices('allowedOccuranceRange', 'allowedOccurrenceRange'),
    )
    occuranceType: Optional[str] = Field(
        min_length=1, default=DEFAULTS["properties"]["occuranceType"],
        validation_alias=AliasChoices('occuranceType', 'occurrenceType'),
    )
    typeCheck: Optional[bool] = Field(default=DEFAULTS["properties"]["typeCheck"])
    shapeCheck: Optional[bool] = Field(default=DEFAULTS["properties"]["shapeCheck"])
    equalNaN: Optional[bool] = Field(default=DEFAULTS["properties"]["equalNaN"])
    ignoreClass: Optional[bool] = Field(default=DEFAULTS["properties"]["ignoreClass"])
    timeout: Optional[float] = Field(ge=0, default=DEFAULTS["properties"]["timeout"])
    tests: List[ComputorTestCollection] = Field(default=[])


class ComputorTestSuite(ComputorBase):
    """Main test suite definition (test.yaml root)."""
    type: Optional[str] = Field(min_length=1, default=DEFAULTS["testsuite"]["type"])
    name: Optional[str] = Field(min_length=1, default=DEFAULTS["testsuite"]["name"])
    description: Optional[str] = Field(
        min_length=1, default=DEFAULTS["testsuite"]["description"]
    )
    version: Optional[str] = Field(
        pattern=VERSION_REGEX, default=DEFAULTS["testsuite"]["version"]
    )
    properties: ComputorTestProperty = Field(default=ComputorTestProperty())


class ComputorSpecification(ComputorBase):
    """Specification for test execution directories."""
    executionDirectory: Optional[str] = Field(
        min_length=1, default=DEFAULTS["specification"]["executionDirectory"]
    )
    studentDirectory: Optional[str] = Field(
        min_length=1, default=DEFAULTS["specification"]["studentDirectory"]
    )
    referenceDirectory: Optional[str] = Field(
        min_length=1, default=DEFAULTS["specification"]["referenceDirectory"]
    )
    testDirectory: Optional[str] = Field(
        min_length=1, default=DEFAULTS["specification"]["testDirectory"]
    )
    outputDirectory: Optional[str] = Field(
        min_length=1, default=DEFAULTS["specification"]["outputDirectory"]
    )
    artifactDirectory: Optional[str] = Field(
        min_length=1, default=DEFAULTS["specification"]["artifactDirectory"]
    )
    testVersion: Optional[str] = Field(
        min_length=1, default=DEFAULTS["specification"]["testVersion"]
    )
    storeGraphicsArtifacts: Optional[bool] = Field(
        default=DEFAULTS["specification"]["storeGraphicsArtifacts"]
    )
    outputName: Optional[str] = Field(
        min_length=1, default=DEFAULTS["specification"]["outputName"]
    )
    isLocalUsage: Optional[bool] = Field(
        default=DEFAULTS["specification"]["isLocalUsage"]
    )
    studentTestCounter: Optional[int] = Field(ge=0, default=None)
