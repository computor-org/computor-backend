"""
Testing backend implementations for different programming languages and testing frameworks.
Provides a flexible system to execute tests using different approaches (subprocess, Pyro RPC, etc.)
"""

import json
import socket
import subprocess
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import Pyro5.api
import Pyro5.errors

from computor_backend.tasks.worker_settings import get_worker_settings

logger = logging.getLogger(__name__)


class TestingBackend(ABC):
    """Abstract base class for testing backends."""

    def __init__(self, service_slug: str = None, language: str = None):
        """Initialize backend with its service slug and language.

        ``language`` comes from ``Service.config.language`` and is what
        actually selects behaviour. ``service_slug`` is carried for logging
        and error messages only — it is the ``meta.yaml``
        ``executionBackend.slug`` contract, an identifier, never a runner
        selector.
        """
        self.service_slug = service_slug
        self.language = language

    @abstractmethod
    async def execute_tests(
        self,
        test_file_path: str,
        spec_file_path: str,
        test_job_config: Dict[str, Any],
        backend_properties: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute tests and return results."""
        pass
    
    @abstractmethod
    def get_backend_type(self) -> str:
        """Return the type identifier for this backend."""
        pass


class MatlabTestingBackend(TestingBackend):
    """MATLAB testing backend using Pyro RPC to communicate with MATLAB server."""
    
    def get_backend_type(self) -> str:
        return "temporal:matlab"
    
    async def execute_tests(
        self,
        test_file_path: str,
        spec_file_path: str,
        test_job_config: Dict[str, Any],
        backend_properties: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute MATLAB tests using Pyro RPC."""
        
        # Get Pyro configuration
        pyro_host = backend_properties.get("pyro_host", "localhost")
        pyro_port = backend_properties.get("pyro_port", 7777)
        pyro_object_id = backend_properties.get("pyro_object_id", "matlab_server")
        
        # If running in Docker, use container hostname
        if get_worker_settings().running_in_docker:
            hostname = socket.gethostname()
            ip_address = socket.gethostbyname(hostname)
            pyro_address = f"PYRO:{pyro_object_id}@{ip_address}:{pyro_port}"
        else:
            pyro_address = f"PYRO:{pyro_object_id}@{pyro_host}:{pyro_port}"
        
        logger.info(f"Connecting to MATLAB server at: {pyro_address}")
        
        try:
            # Connect to MATLAB server via Pyro
            matlab_server = Pyro5.api.Proxy(pyro_address)

            # Get timeout from backend properties or test config (default: 5 minutes)
            timeout_seconds = backend_properties.get(
                "timeout_seconds",
                test_job_config.get("timeout_seconds", 45)
            )

            logger.info(f"Executing MATLAB test with {timeout_seconds}s timeout")

            # Call MATLAB test execution with timeout
            result_json = matlab_server.test_student_example(
                test_file_path,
                spec_file_path,
                timeout_seconds
            )

            logger.info(f"MATLAB test result: {result_json}")

            # Parse the JSON result
            result = json.loads(result_json)

            # Check if there was a timeout
            if result.get("timeout"):
                return {
                    "passed": 0,
                    "failed": 1,
                    "total": 1,
                    "error": f"Execution timeout: Test exceeded {result.get('timeout_seconds', timeout_seconds)} seconds. "
                             "This usually indicates an infinite loop in the code.",
                    "details": result.get("details", {}),
                    "timeout": True
                }

            # Check if there was an exception
            if "details" in result and isinstance(result["details"], dict):
                if "exception" in result["details"]:
                    return {
                        "passed": 0,
                        "failed": 1,
                        "total": 1,
                        "error": result["details"]["exception"].get("message", "MATLAB error"),
                        "details": result["details"]
                    }

            # Parse successful test results
            # Adapt the MATLAB output format to our standard format
            return {
                "passed": result.get("passed", 0),
                "failed": result.get("failed", 0),
                "total": result.get("total", 1),
                "details": result.get("details", {})
            }
            
        except Pyro5.errors.CommunicationError as e:
            logger.error(f"Failed to connect to MATLAB server: {e}")
            return {
                "passed": 0,
                "failed": 1,
                "total": 1,
                "error": f"Failed to connect to MATLAB server: {e}",
                "details": {"communication_error": str(e)}
            }
        except Exception as e:
            logger.error(f"Error executing MATLAB tests: {e}")
            return {
                "passed": 0,
                "failed": 1,
                "total": 1,
                "error": str(e),
                "details": {"exception": str(e)}
            }


class ComputorTestingBackend(TestingBackend):
    """
    Computor testing backend using computor-testing framework.

    Supports multiple languages through a single CLI:
    - Python
    - Octave (GNU Octave, not MATLAB)
    - R
    - Julia
    - C/C++
    - Fortran
    - Document/Text analysis

    Uses the computor-test CLI which wraps pytest-based testing.
    """

    # ``doc`` is accepted as an alias because the historical slug suffix was
    # ``.doc`` while the computor-test subcommand is ``document``.
    _SUBCOMMAND_ALIASES = {"doc": "document"}

    def get_backend_type(self) -> str:
        return "computor-testing"

    async def execute_tests(
        self,
        test_file_path: str,
        spec_file_path: str,
        test_job_config: Dict[str, Any],
        backend_properties: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute tests using computor-test CLI.

        The computor-testing framework now accepts absolute paths in specification.yaml,
        so we can pass through the paths directly from temporal_student_testing.py.

        Args:
            test_file_path: Path to test.yaml file
            spec_file_path: Path to specification.yaml file (with absolute paths)
            test_job_config: Test job configuration
            backend_properties: Merged configuration from service.config and service_type.properties

        Returns:
            Test results dictionary (or None to read from file)
        """
        logging.basicConfig(level=logging.INFO)

        # The language comes from Service.config.language, resolved by the
        # factory. There is deliberately no slug-based fallback: the slug is
        # the meta.yaml contract, not a runner selector, and guessing from it
        # is what made every non-itpcp.* slug unusable.
        language = self.language
        if not language:
            raise ValueError(
                "No testing language configured for service "
                f"'{test_job_config.get('testing_service_slug') or self.service_slug}'. "
                "Set config.language on the service."
            )
        language = self._SUBCOMMAND_ALIASES.get(language, language)

        # Get configuration with fallbacks. TESTING_EXECUTABLE has no static
        # default in worker_settings, so this site keeps its own "computor-test".
        settings = get_worker_settings()
        testing_executable = backend_properties.get(
            "testing_executable",
            settings.testing_executable
            if settings.testing_executable is not None
            else "computor-test",
        )

        # Build command: computor-test <language> run -T <test.yaml> -s <spec.yaml>
        # Note: -t (target) parameter is optional, specification has executionDirectory
        cmd_parts = [
            testing_executable,
            language,
            "run",
            "-T", test_file_path,
            "-s", spec_file_path,
        ]

        # Add verbosity if specified
        verbosity = backend_properties.get("verbosity", 0)
        if verbosity > 0:
            cmd_parts.extend(["-v", str(verbosity)])

        cmd = " ".join(cmd_parts)
        logger.info(f"Executing computor-test command: {cmd}")

        try:
            # Execute test command
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=backend_properties.get("timeout_seconds", 300)
            )

            # Log output for debugging
            logger.info(f"Test command executed with return code: {result.returncode}")
            if result.stdout:
                logger.info(f"Test stdout: {result.stdout[:500]}...")
            if result.stderr:
                logger.warning(f"Test stderr: {result.stderr[:500]}...")

            # computor-test writes results to testSummary.json in output directory
            # Return None to signal that results should be read from file
            return None

        except subprocess.TimeoutExpired as e:
            logger.error(f"Test execution timed out: {e}")
            return {
                "passed": 0,
                "failed": 1,
                "total": 1,
                "error": f"Test execution timed out after {backend_properties.get('timeout_seconds', 300)} seconds",
                "details": {"timeout": True}
            }
        except Exception as e:
            logger.error(f"Error executing computor-test: {e}")
            return {
                "passed": 0,
                "failed": 1,
                "total": 1,
                "error": str(e),
                "details": {"exception": str(e)}
            }


class TestingBackendFactory:
    """Factory for creating testing backend instances, keyed by language.

    Dispatch is on ``Service.config.language``, never on the service slug.
    The slug is the contract between an example's ``meta.yaml``
    (``properties.executionBackend.slug``) and a ``Service`` row — an
    identifier chosen by whoever registers the service. It used to double as
    a lookup key into a hardcoded table here, which meant only the eight
    ``itpcp.exec.*`` names known to this file could ever run: registering a
    testing system under any other name produced a service that bound to
    examples correctly and then died at execution.

    Adding a testing system is now a data change, not a code change.
    """

    _language_backends: Dict[str, type[TestingBackend]] = {
        # computor-test CLI, one subcommand per language
        "python": ComputorTestingBackend,
        "octave": ComputorTestingBackend,      # GNU Octave, not MATLAB
        "r": ComputorTestingBackend,
        "julia": ComputorTestingBackend,
        "c": ComputorTestingBackend,
        "cpp": ComputorTestingBackend,
        "fortran": ComputorTestingBackend,
        "document": ComputorTestingBackend,
        "doc": ComputorTestingBackend,         # alias for 'document'
        # MATLAB is a separate system: Pyro5 RPC to the MATLAB engine
        "matlab": MatlabTestingBackend,
    }

    @classmethod
    def register_language_backend(cls, language: str, backend_class: type[TestingBackend]):
        """Register a testing backend implementation for a language."""
        cls._language_backends[language.lower()] = backend_class

    @classmethod
    def create_backend(cls, service_slug: str, language: Optional[str] = None) -> TestingBackend:
        """Create a testing backend for ``language``.

        Raises with an actionable message when the service carries no
        language, which is the one configuration mistake that can produce an
        otherwise-valid testing service.
        """
        if not language:
            raise ValueError(
                f"Service '{service_slug}' has no testing language configured. "
                f"Set config.language on the service to one of: "
                f"{sorted(cls._language_backends)}"
            )

        key = language.strip().lower()
        backend_class = cls._language_backends.get(key)
        if not backend_class:
            raise ValueError(
                f"Unsupported testing language '{language}' on service "
                f"'{service_slug}'. Supported languages: "
                f"{sorted(cls._language_backends)}"
            )
        return backend_class(service_slug=service_slug, language=key)

    @classmethod
    def get_available_languages(cls) -> list[str]:
        """Languages a service may set in ``config.language``."""
        return sorted(cls._language_backends)


async def execute_tests_with_backend(
    service_slug: str,
    test_file_path: str,
    spec_file_path: str,
    test_job_config: Dict[str, Any],
    service_config: Optional[Dict[str, Any]] = None,
    service_type_config: Optional[Dict[str, Any]] = None,
    backend_properties: Optional[Dict[str, Any]] = None  # Deprecated, for backward compatibility
) -> Dict[str, Any]:
    """
    Execute tests using the appropriate backend based on service slug.

    Configuration priority (highest to lowest):
    1. service_config (from Service.config - instance-specific)
    2. service_type_config (from ServiceType.properties - type defaults)
    3. backend_properties (deprecated - for backward compatibility)
    4. Environment variables

    Args:
        service_slug: Service slug identifying the backend (e.g., "itpcp.exec.py")
        test_file_path: Path to test file (test.yaml)
        spec_file_path: Path to specification file (specification.yaml)
        test_job_config: Test job configuration (contains student_path, testing_service_slug, etc.)
        service_config: Configuration from Service.config (instance-specific overrides)
        service_type_config: Configuration from ServiceType.properties (type-level defaults)
        backend_properties: Deprecated - use service_config and service_type_config instead

    Returns:
        Test results dictionary (or None to read from testSummary.json)
    """
    try:
        # Merge configurations with proper priority
        # Priority: service_config > service_type_config > backend_properties
        merged_properties = {}

        # Lowest priority: deprecated backend_properties
        if backend_properties:
            merged_properties.update(backend_properties)

        # Medium priority: service type defaults
        if service_type_config and isinstance(service_type_config, dict):
            type_props = service_type_config.get("properties", {})
            if isinstance(type_props, dict):
                merged_properties.update(type_props)

        # Highest priority: service instance config
        if service_config and isinstance(service_config, dict):
            instance_config = service_config.get("config", service_config)
            if isinstance(instance_config, dict):
                merged_properties.update(instance_config)

        logger.info(f"Merged backend properties for {service_slug}: {merged_properties}")

        # `language` rides in on the merged config: Service.config wins over
        # ServiceType.properties, so a type can supply a default and a service
        # can override it.
        backend = TestingBackendFactory.create_backend(
            service_slug, language=merged_properties.get("language")
        )
        return await backend.execute_tests(
            test_file_path,
            spec_file_path,
            test_job_config,
            merged_properties
        )
    except Exception as e:
        logger.error(f"Error creating or executing backend {service_slug}: {e}")
        return {
            "passed": 0,
            "failed": 1,
            "total": 1,
            "error": f"Backend error: {e}",
            "details": {"service_slug": service_slug, "error": str(e)}
        }