"""
Utilities package for computor_backend.
"""

from .color_validation import (
    is_valid_color, validate_color, is_valid_hex_color, 
    is_valid_rgb_color, is_valid_hsl_color, is_valid_css_named_color,
    get_color_examples
)

from .docker_utils import (
    is_running_in_docker, get_docker_host_ip, transform_localhost_url,
    transform_gitlab_url
)

__all__ = [
    # Color validation
    'is_valid_color', 'validate_color', 'is_valid_hex_color', 
    'is_valid_rgb_color', 'is_valid_hsl_color', 'is_valid_css_named_color',
    'get_color_examples',
    # Docker utilities
    'is_running_in_docker', 'get_docker_host_ip', 'transform_localhost_url',
    'transform_gitlab_url'
]