import yaml
from abc import ABC
from enum import Enum
from pydantic_yaml import to_yaml_str
from typing import Any, List, Optional, TYPE_CHECKING
from pydantic import BaseModel, ConfigDict, Field, field_validator

if TYPE_CHECKING:
    from computor_types.users import UserGet

class DeploymentFactory:

  @staticmethod
  def read_deployment_from_string(classname, yamlstring: str):
    return classname(**yaml.safe_load(yamlstring))

  @staticmethod
  def read_deployment_from_file(classname, filename: str):
    with open(filename, "r") as file:
      if classname != None:
        return classname(**yaml.safe_load(file))
      else:
        return yaml.safe_load(file)
    
  @staticmethod
  def read_deployment_from_file_raw(filename: str):
    with open(filename, "r") as file:
      return yaml.safe_load(file)
    
class BaseDeployment(BaseModel):

  def get_deployment(self):
    return to_yaml_str(self,exclude_none=True,exclude_unset=True)

  def write_deployment(self, filename: str):
    with open(filename, "w") as file:
      file.write(self.get_deployment())

class CodeabilityReleaseBuilder(ABC):

  def get_directory_testing():
    pass

  def get_directory_student_template():
    pass
  
  def create_course_release(self) -> list[str]:
    pass

  def create_release(self, release_dir: str) -> list[str]:
    pass

  async def create_student_project(self, user: 'UserGet'):
    pass

class GitlabGroupProjectConfig(BaseDeployment):
  name: Optional[str] = None
  path: str

  @property
  def display_name(self) -> str:
    if self.name == None:
      return self.path
    else:
      return self.name
  
class CourseProjectsConfig(BaseDeployment):
  tests: GitlabGroupProjectConfig
  student_template : GitlabGroupProjectConfig
  reference : GitlabGroupProjectConfig
  images: GitlabGroupProjectConfig 
  documents: GitlabGroupProjectConfig

class ApiConfig(BaseDeployment):
  user: str
  password: str
  url: str

class RepositoryConfig(BaseDeployment):
  settings: Optional[dict] = Field(default_factory=dict)

class GitLabConfigGet(RepositoryConfig):
  url: Optional[str] = None
  full_path: Optional[str] = None
  directory: Optional[str] = None
  registry: Optional[str] = None
  parent: Optional[int] = None
  # Enhanced GitLab properties
  group_id: Optional[int] = None
  parent_id: Optional[int] = None
  namespace_id: Optional[int] = None
  namespace_path: Optional[str] = None
  web_url: Optional[str] = None
  visibility: Optional[str] = None
  last_synced_at: Optional[str] = None

class GitLabConfig(GitLabConfigGet):
  token: Optional[str] = None

# class GitHubConfig(RepositoryConfig):
#   pass

class TypeConfig(BaseDeployment):
  kind: str = Field()
  slug: str = Field()
  title: str = Field()
  color: Optional[str | None] = None
  description: Optional[str | None] = None
  properties: dict = {}

class CourseGroupConfig(BaseDeployment):
  name: str = Field()

class ExecutionBackendConfig(BaseDeployment):
  slug: str
  type: str
  settings: Optional[dict] = None

class CourseExecutionBackendConfig(BaseDeployment):
  slug: str
  settings: Optional[dict] = None

class FileSourceConfig(BaseDeployment):
  url: str
  token: Optional[str] = None

class CourseSettingsConfig(BaseDeployment):

  model_config = ConfigDict(
      extra='allow',
  )

  source: Optional[FileSourceConfig] = None

class CourseConfig(BaseDeployment):
  name: str
  path: str
  description: Optional[str] = None
  executionBackends: Optional[List[CourseExecutionBackendConfig]] = None
  settings: Optional[CourseSettingsConfig] = None

class CourseFamilyConfig(BaseDeployment):
  name: str
  path: str
  description: Optional[str] = None
  settings: Optional[dict] = None

class OrganizationConfig(BaseDeployment):
  name: str
  path: str
  description: Optional[str] = None
  settings: Optional[dict] = None
  gitlab: Optional[GitLabConfig] = None
  #github: Optional[GitHubConfig] = None

class ComputorDeploymentConfig(BaseDeployment):
  organization: OrganizationConfig
  courseFamily: CourseFamilyConfig
  course: CourseConfig
  settings: Optional[dict] = None

COURSE_DEFAULT_DEPLOYMENT = ComputorDeploymentConfig(
  organization=OrganizationConfig(
    path="computor",
    name="Computor Playground",
    gitlab=GitLabConfig(
      provider_url="https://gitlab.com",
      token="-",
      parent=0
    ),
  ),
  courseFamily=CourseFamilyConfig(
    path="progphys",
    name="Programmieren in der Physik",
  ),
  course=CourseConfig(
    path="2026.python",
    name="Python",
    executionBackends=[
      CourseExecutionBackendConfig(
        slug="itp-python"
    )],
    settings=CourseSettingsConfig(
      source=FileSourceConfig(
        url="https://gitlab.com/../../assignments.git",
        token="-"
      )
    )
  )
)

DIRECTORIES = [
  "studentDirectory",
  "referenceDirectory",
  "testDirectory",
  "outputDirectory",
  "artifactDirectory",
]

class StatusEnum(str, Enum):
  scheduled = "SCHEDULED"
  completed = "COMPLETED"
  timedout = "TIMEDOUT"
  crashed = "CRASHED"
  cancelled = "CANCELLED"
  skipped = "SKIPPED"
  failed = "FAILED"
  # following not used yet:
  #pending = "PENDING"
  #running = "RUNNING"

class ResultEnum(str, Enum):
  passed = "PASSED"
  failed = "FAILED"
  skipped = "SKIPPED"
    
class QualificationEnum(str, Enum):
  verifyEqual = "verifyEqual"
  matches = "matches"
  contains = "contains"
  startsWith = "startsWith"
  endsWith = "endsWith"
  count = "count"
  regexp = "regexp"

class TypeEnum(str, Enum):
  variable = "variable"
  graphics = "graphics"
  structural = "structural"
  linting = "linting"
  exist = "exist"
  error = "error"
  warning = "warning"
  help = "help"
  stdout = "stdout"

class LanguageEnum(str, Enum):
  de = "de"
  en = "en"

class MetaTypeEnum(str, Enum):
  Course = "course"
  Unit = "unit"
  Assignment = "assignment"

VERSION_REGEX = "^([1-9]\d*|0)(\.(([1-9]\d*)|0)){0,3}$"
#todo:
#url + email regex

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
        "type": "python",
        "name": "Python Test Suite",
        "description": "Checks subtests and graphics",
        "version": "1.0",
    },
    "properties": {
        "qualification": QualificationEnum.verifyEqual,
        "failureMessage": "Some or all tests failed",
        "successMessage": "Congratulations! All tests passed",
        "relativeTolerance": 1.0e-15,
        "absoluteTolerance": 0.0,
        "timeout": 180.0,
        "allowedOccuranceRange": [0, 0],
        "occuranceType": "NAME",
    },
    "meta": {
        "version": "1.0",
        "type": MetaTypeEnum.Assignment,
        "title": "TITLE",
        "description": "DESCRIPTION",
        "language": LanguageEnum.en,
        "license": "Not specified",
    },
    "person": {
        "name": "unknown",
        "email": "unknown@unknown.at",
        "affiliation": "TU Graz",
    },
}

class CodeAbilityBase(BaseModel):
  model_config = ConfigDict(
      # extra="forbid",
      use_enum_values=True,
      validate_assignment=True,
      coerce_numbers_to_str=True
  )

  def get_deployment(self):
    return to_yaml_str(self,exclude_none=True)

  def write_deployment(self, filename: str):
    with open(filename, "w") as file:
      file.write(self.get_deployment())

class CodeAbilityTestCommon(BaseModel):
  failureMessage: Optional[str] = Field(min_length=1, default=None)
  successMessage: Optional[str] = Field(min_length=1, default=None)
  qualification: Optional[QualificationEnum] = Field(default=None, validate_default=True)
  relativeTolerance: Optional[float] = Field(gt=0, default=None)
  absoluteTolerance: Optional[float] = Field(ge=0, default=None)
  allowedOccuranceRange: Optional[List[int]] = Field(min_length=2, max_length=2, default=None)
  occuranceType: Optional[str] = Field(min_length=1, default=None)
  verbosity: Optional[int] = Field(ge=0, le=3, default=None)

class CodeAbilityTestCollectionCommon(CodeAbilityTestCommon):
  storeGraphicsArtifacts: Optional[bool] = Field(default=None)
  competency: Optional[str] = Field(min_length=1, default=None)
  timeout: Optional[float] = Field(ge=0, default=None)

class CodeAbilityTest(CodeAbilityBase, CodeAbilityTestCommon):
  name: str = Field(min_length=1)
  value: Optional[Any] = Field(default=None)
  evalString: Optional[str] = Field(min_length=1, default=None)
  pattern: Optional[str] = Field(min_length=1, default=None)
  countRequirement: Optional[int] = Field(ge=0, default=None)

class CodeAbilityTestCollection(CodeAbilityBase, CodeAbilityTestCollectionCommon):
  type: Optional[TypeEnum] = Field(default=TypeEnum.variable, validate_default=True)
  name: str = Field(min_length=1)
  description: Optional[str] = Field(default=None)
  successDependency: Optional[str | int | List[str | int]] = Field(default=None)
  setUpCodeDependency: Optional[str] = Field(min_length=1, default=None)
  entryPoint: Optional[str] = Field(min_length=1, default=None)
  inputAnswers: Optional[str | List[str]] = Field(default=None)
  setUpCode: Optional[str | List[str]] = Field(default=None)
  tearDownCode: Optional[str | List[str]] = Field(default=None)
  id: Optional[str] = Field(min_length=1, default=None)
  file: Optional[str] = Field(min_length=1, default=None)
  tests: List[CodeAbilityTest]

class CodeAbilityTestProperty(CodeAbilityBase, CodeAbilityTestCollectionCommon):
  qualification: Optional[QualificationEnum] = Field(default=DEFAULTS["properties"]["qualification"], validate_default=True)
  failureMessage: Optional[str] = Field(min_length=1, default=DEFAULTS["properties"]["failureMessage"])
  successMessage: Optional[str] = Field(min_length=1, default=DEFAULTS["properties"]["successMessage"])
  relativeTolerance: Optional[float] = Field(gt=0, default=DEFAULTS["properties"]["relativeTolerance"])
  absoluteTolerance: Optional[float] = Field(ge=0, default=DEFAULTS["properties"]["absoluteTolerance"])
  allowedOccuranceRange: Optional[List[int]] = Field(min_length=2, max_length=2, default=DEFAULTS["properties"]["allowedOccuranceRange"])
  occuranceType: Optional[str] = Field(min_length=1, default=DEFAULTS["properties"]["occuranceType"])
  timeout: Optional[float] = Field(ge=0, default=DEFAULTS["properties"]["timeout"])
  tests: List[CodeAbilityTestCollection] = Field(default=[])

class CodeAbilityTestSuite(CodeAbilityBase):
  type: Optional[str] = Field(min_length=1, default=DEFAULTS["testsuite"]["type"])
  name: Optional[str] = Field(min_length=1, default=DEFAULTS["testsuite"]["name"])
  description: Optional[str] = Field(default=None)
  version: Optional[str] = Field(pattern=VERSION_REGEX, default=DEFAULTS["testsuite"]["version"])
  properties: CodeAbilityTestProperty = Field(default=CodeAbilityTestProperty())

class CodeAbilitySpecification(CodeAbilityBase):
  executionDirectory: Optional[str] = Field(min_length=1, default=DEFAULTS["specification"]["executionDirectory"])
  studentDirectory: Optional[str] = Field(min_length=1, default=DEFAULTS["specification"]["studentDirectory"])
  referenceDirectory: Optional[str] = Field(min_length=1, default=DEFAULTS["specification"]["referenceDirectory"])
  testDirectory: Optional[str] = Field(min_length=1, default=DEFAULTS["specification"]["testDirectory"])
  outputDirectory: Optional[str] = Field(min_length=1, default=DEFAULTS["specification"]["outputDirectory"])
  artifactDirectory: Optional[str] = Field(min_length=1, default=DEFAULTS["specification"]["artifactDirectory"])
  testVersion: Optional[str] = Field(min_length=1, default=DEFAULTS["specification"]["testVersion"])
  storeGraphicsArtifacts: Optional[bool] = Field(default=DEFAULTS["specification"]["storeGraphicsArtifacts"])
  outputName: Optional[str] = Field(min_length=1, default=DEFAULTS["specification"]["outputName"])
  isLocalUsage: Optional[bool] = Field(default=DEFAULTS["specification"]["isLocalUsage"])
  studentTestCounter: Optional[int] = Field(ge=0, default=None)

class CodeAbilityLink(CodeAbilityBase):
  description: str = Field(min_length=0)
  url: str = Field(min_length=1)

class CodeAbilityPerson(CodeAbilityBase):
  name: Optional[str] = Field(min_length=1, default=None)
  email: Optional[str] = Field(min_length=1, default=None)
  affiliation: Optional[str] = Field(min_length=1, default=None)

class CodeAbilityMetaProperty(CodeAbilityBase):
  studentSubmissionFiles: Optional[List[str]] = Field(default=[])
  additionalFiles: Optional[List[str]] = Field(default=[])
  testFiles: Optional[List[str]] = Field(default=[])
  studentTemplates: Optional[List[str]] = Field(default=[])
  executionBackend: Optional[CourseExecutionBackendConfig] = None
  
  maxTestRuns: Optional[int] = None
  maxSubmissions: Optional[int] = None
  maxGroupSize: Optional[int] = None

  @field_validator('maxTestRuns', 'maxSubmissions', 'maxGroupSize', 'executionBackend', mode='before')
  @classmethod
  def empty_list_to_none(cls, value):
      if isinstance(value, list) and len(value) == 0:
          return None
      return value

class CodeAbilityReportSummary(CodeAbilityBase):
  total: int = Field(ge=0, default=0)
  passed: int = Field(ge=0, default=0)
  failed: int = Field(ge=0, default=0)
  skipped: int = Field(ge=0, default=0)

class CodeAbilityReleaseMeta(CodeAbilityBase):
  version: Optional[str] = Field(pattern=VERSION_REGEX, default=DEFAULTS["meta"]["version"])
  kind: Optional[MetaTypeEnum] = Field(default=DEFAULTS["meta"]["type"], validate_default=True)
  title: Optional[str] = Field(min_length=1, default=DEFAULTS["meta"]["title"])
  description: Optional[str] = Field(default=None)
  language: Optional[LanguageEnum] = Field(default=DEFAULTS["meta"]["language"], validate_default=True)
  license: Optional[str] = Field(min_length=1, default=DEFAULTS["meta"]["license"])
  authors: Optional[List[CodeAbilityPerson]] = Field(default=[])
  maintainers: Optional[List[CodeAbilityPerson]] = Field(default=[])
  links: Optional[List[CodeAbilityLink]] = Field(default=[])
  supportingMaterial: Optional[List[CodeAbilityLink]] = Field(default=[])
  keywords: Optional[List[str]] = Field(default=[])
  properties: Optional[CodeAbilityMetaProperty] = Field(default=CodeAbilityMetaProperty())

  @field_validator('description', mode='before')
  @classmethod
  def empty_list_to_none(cls, value):
      if isinstance(value, list) and len(value) == 0:
          return None
      return value

class CodeAbilityMeta(CodeAbilityReleaseMeta):
  type: str
  testDependencies: Optional[List[str]] = Field(default=[])

class CodeAbilityCourseMeta(CodeAbilityReleaseMeta):
  contentTypes: Optional[List[TypeConfig]] = []
  executionBackends: Optional[List[CourseExecutionBackendConfig]] = []

class CodeAbilityUnitMeta(CodeAbilityReleaseMeta):
  type: str
  
class CodeAbilityReportProperties(CodeAbilityBase):
  timestamp: Optional[str] = Field(default=None)
  type: Optional[str] = Field(default=None)
  version: Optional[str] = Field(default=None)
  name: Optional[str] = Field(default=None)
  description: Optional[str] = Field(default=None)
  status: Optional[StatusEnum] = Field(default=None, validate_default=True)
  result: Optional[ResultEnum] = Field(default=None, validate_default=True)
  summary: Optional[CodeAbilityReportSummary] = Field(default=None)
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
  
class CodeAbilityReportSub(CodeAbilityReportProperties):
    pass

class CodeAbilityReportMain(CodeAbilityReportProperties):
    tests: Optional[List[CodeAbilityReportSub]] = Field(default=None)

class CodeAbilityReport(CodeAbilityReportProperties):
    tests: Optional[List[CodeAbilityReportMain]] = Field(default=None)