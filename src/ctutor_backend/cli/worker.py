"""
CLI commands for managing task workers - redirects to Temporal implementation.
"""

# Import everything from temporal worker
from .temporal_worker import *

# For backwards compatibility
__all__ = ['worker', 'start', 'status', 'test_job']