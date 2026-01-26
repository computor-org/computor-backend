"""
Testing backend implementations for different programming languages and testing frameworks.
Provides a flexible system to execute tests using different approaches (subprocess, Pyro RPC, etc.)
"""

import os
import json
import socket
import subprocess
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import Pyro5.api
import Pyro5.errors

logger = logging.getLogger(__name__)


class TestingBackend(ABC):
    """Abstract base class for testing backends."""

    def __init__(self, service_slug: str = None):
        """Initialize backend with optional service slug."""
        self.service_slug = service_slug

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


class PythonTestingBackend(TestingBackend):
    """Python testing backend using subprocess execution."""
    
    def get_backend_type(self) -> str:
        return "temporal:python"
    
    async def execute_tests(
        self,
        test_file_path: str,
        spec_file_path: str,
        test_job_config: Dict[str, Any],
        backend_properties: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute Python tests using subprocess."""
        logging.basicConfig(level=logging.INFO)
        # Get configuration from backend properties
        testing_executable = backend_properties.get(
            "testing_executable",
            os.environ.get("TESTING_EXECUTABLE", "/tmp/engine/catester/testing.py run")
        )
        runtime_environment = backend_properties.get(
            "runtime_environment",
            os.environ.get("RUNTIME_ENVIRONMENT", "python3")
        )
        
        # Build command
        test_env_exec = f"{runtime_environment} {testing_executable} --test {test_file_path} --spec {spec_file_path}"
        logger.info(f"Executing Python test command: {test_env_exec}")
        
        try:
            # Execute test command
            result = subprocess.run(
                test_env_exec,
                shell=True,
                capture_output=True,
                text=True,
                timeout=backend_properties.get("timeout", 300)  # 5 minutes default
            )
            
            # Log output for debugging
            logger.info(f"Test command executed with return code: {result.returncode}")
            if result.stdout:
                logger.info(f"Test stdout: {result.stdout[:500]}...")
            if result.stderr:
                logger.warning(f"Test stderr: {result.stderr[:500]}...")

            # Python test backend writes results to file (testSummary.json)
            # The return value here is ignored - results are read from file
            # Just return None to indicate execution completed
            return None
            
        except subprocess.TimeoutExpired as e:
            logger.error(f"Test execution timed out: {e}")
            return {
                "passed": 0,
                "failed": 1,
                "total": 1,
                "error": "Test execution timed out",
                "details": {"timeout": True}
            }
        except Exception as e:
            logger.error(f"Error executing Python tests: {e}")
            return {
                "passed": 0,
                "failed": 1,
                "total": 1,
                "error": str(e),
                "details": {"exception": str(e)}
            }


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
        if os.environ.get("RUNNING_IN_DOCKER"):
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

    # Language slug to computor-test subcommand mapping
    LANGUAGE_MAP = {
        "itpcp.exec.py": "python",
        "itpcp.exec.oct": "octave",
        "itpcp.exec.r": "r",
        "itpcp.exec.julia": "julia",
        "itpcp.exec.c": "c",
        "itpcp.exec.fortran": "fortran",
        "itpcp.exec.doc": "document",
    }

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

        # Determine language from service slug
        language = self._get_language_from_slug(
            test_job_config.get("testing_service_slug") or self.service_slug
        )

        if not language:
            raise ValueError(
                f"Could not determine language for service slug: "
                f"{test_job_config.get('testing_service_slug')}"
            )

        # Get configuration with fallbacks
        testing_executable = backend_properties.get(
            "testing_executable",
            os.environ.get("TESTING_EXECUTABLE", "computor-test")
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

    def _get_language_from_slug(self, service_slug: str) -> Optional[str]:
        """Map service slug to computor-test language name."""
        if not service_slug:
            return None
        return self.LANGUAGE_MAP.get(service_slug.lower())


class JavaTestingBackend(TestingBackend):
    """Java testing backend using JUnit or similar frameworks."""

    def get_backend_type(self) -> str:
        return "temporal:java"

    async def execute_tests(
        self,
        test_file_path: str,
        spec_file_path: str,
        test_job_config: Dict[str, Any],
        backend_properties: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute Java tests."""

        # Example implementation for Java testing
        java_command = backend_properties.get("java_command", "java")
        test_runner = backend_properties.get("test_runner", "junit")

        # Build command based on test runner
        if test_runner == "junit":
            cmd = f"{java_command} -cp .:junit.jar org.junit.runner.JUnitCore {test_file_path}"
        else:
            cmd = f"{java_command} {test_file_path}"

        logger.info(f"Executing Java test command: {cmd}")

        # Similar subprocess execution as Python
        # ... (implementation details)

        return {
            "passed": 0,
            "failed": 0,
            "total": 0,
            "details": {"message": "Java testing backend not fully implemented"}
        }


class TestingBackendFactory:
    """Factory for creating testing backend instances based on service slug."""

    _backends: Dict[str, type[TestingBackend]] = {
        # ComputorTestingBackend for computor-testing framework (multi-language)
        "itpcp.exec.py": ComputorTestingBackend,
        "itpcp.exec.oct": ComputorTestingBackend,      # Octave (not MATLAB!)
        "itpcp.exec.r": ComputorTestingBackend,
        "itpcp.exec.julia": ComputorTestingBackend,
        "itpcp.exec.c": ComputorTestingBackend,
        "itpcp.exec.fortran": ComputorTestingBackend,
        "itpcp.exec.doc": ComputorTestingBackend,

        # MATLAB - separate system with Pyro5 RPC (unchanged)
        "itpcp.exec.mat": MatlabTestingBackend,

        # Legacy backends (deprecated but kept for backward compatibility)
        "temporal:python": PythonTestingBackend,
        "temporal:matlab": MatlabTestingBackend,
        "temporal:java": JavaTestingBackend,
    }

    @classmethod
    def register_backend(cls, service_slug: str, backend_class: type[TestingBackend]):
        """Register a new testing backend for a service slug."""
        cls._backends[service_slug] = backend_class

    @classmethod
    def create_backend(cls, service_slug: str) -> TestingBackend:
        """Create a testing backend instance based on service slug."""
        backend_class = cls._backends.get(service_slug.lower())
        if not backend_class:
            raise ValueError(f"Unknown testing backend for service: {service_slug}. Available: {list(cls._backends.keys())}")
        return backend_class(service_slug=service_slug)

    @classmethod
    def get_available_backends(cls) -> list[str]:
        """Get list of available backend types."""
        return list(cls._backends.keys())


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

        # Create and execute backend
        backend = TestingBackendFactory.create_backend(service_slug)
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