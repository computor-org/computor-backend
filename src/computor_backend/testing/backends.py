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
            
            # Parse output
            output = result.stdout
            logger.info(f"Test output: {output}")
            
            # Try to parse JSON output if available
            try:
                test_results = json.loads(output)
            except json.JSONDecodeError:
                # If not JSON, create basic result structure
                test_results = {
                    "passed": 1 if result.returncode == 0 else 0,
                    "failed": 0 if result.returncode == 0 else 1,
                    "total": 1,
                    "details": {
                        "stdout": result.stdout,
                        "stderr": result.stderr,
                        "returncode": result.returncode
                    }
                }
            
            return test_results
            
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
            
            # Extract test metadata from job config
            test_number = test_job_config.get("test_number", -1)
            submission_number = test_job_config.get("submission_number", -1)
            submit = test_job_config.get("submit", False)
            
            # Call MATLAB test execution
            result_json = matlab_server.test_student_example(
                test_file_path,
                spec_file_path,
                submit,
                test_number,
                submission_number
            )
            
            logger.info(f"MATLAB test result: {result_json}")
            
            # Parse the JSON result
            result = json.loads(result_json)
            
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
    """Factory for creating testing backend instances based on type."""
    
    _backends: Dict[str, type[TestingBackend]] = {
        "temporal:python": PythonTestingBackend,
        "temporal:matlab": MatlabTestingBackend,
        "temporal:java": JavaTestingBackend,
    }
    
    @classmethod
    def register_backend(cls, backend_type: str, backend_class: type[TestingBackend]):
        """Register a new testing backend type."""
        cls._backends[backend_type] = backend_class
    
    @classmethod
    def create_backend(cls, backend_type: str) -> TestingBackend:
        """Create a testing backend instance based on type."""
        backend_class = cls._backends.get(backend_type.lower())
        if not backend_class:
            raise ValueError(f"Unknown testing backend type: {backend_type}")
        return backend_class()
    
    @classmethod
    def get_available_backends(cls) -> list[str]:
        """Get list of available backend types."""
        return list(cls._backends.keys())


async def execute_tests_with_backend(
    backend_type: str,
    test_file_path: str,
    spec_file_path: str,
    test_job_config: Dict[str, Any],
    backend_properties: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Execute tests using the appropriate backend based on type.
    
    Args:
        backend_type: Type of testing backend (python, matlab, java, etc.)
        test_file_path: Path to test file
        spec_file_path: Path to specification file
        test_job_config: Test job configuration
        backend_properties: Backend-specific properties
    
    Returns:
        Test results dictionary
    """
    try:
        backend = TestingBackendFactory.create_backend(backend_type)
        return await backend.execute_tests(
            test_file_path,
            spec_file_path,
            test_job_config,
            backend_properties
        )
    except Exception as e:
        logger.error(f"Error creating or executing backend {backend_type}: {e}")
        return {
            "passed": 0,
            "failed": 1,
            "total": 1,
            "error": f"Backend error: {e}",
            "details": {"backend_type": backend_type, "error": str(e)}
        }