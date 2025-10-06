"""
Test color validation system.
"""

import pytest
from computor_backend.utils.color_validation import (
    is_valid_color, validate_color, is_valid_hex_color,
    is_valid_rgb_color, is_valid_hsl_color, is_valid_css_named_color,
    get_color_examples
)
from computor_types.course_content_types import (
    CourseContentTypeCreate, CourseContentTypeUpdate
)


@pytest.mark.unit
class TestColorValidationFunctions:
    """Test color validation utility functions."""
    
    @pytest.mark.parametrize("color", [
        # Hex colors
        '#FF5733', '#ff5733', '#123', '#123456', '#12345678',
        # RGB/RGBA
        'rgb(255, 87, 51)', 'rgba(255, 87, 51, 0.8)',
        # HSL/HSLA
        'hsl(9, 100%, 60%)', 'hsla(9, 100%, 60%, 0.8)',
        # Named colors
        'red', 'blue', 'green', 'tomato', 'lightblue', 'darkslategray',
        # Tailwind colors
        'amber', 'emerald', 'sky', 'rose'
    ])
    def test_valid_colors(self, color):
        """Test that valid colors are accepted."""
        assert is_valid_color(color) is True
        normalized = validate_color(color)
        assert normalized is not None
    
    @pytest.mark.parametrize("color", [
        'invalid-color', '#GGG', 'rgb(300, 300, 300)', 'hsl(400, 150%, 150%)',
        '', 123, 'rgb(255, 255)', 'rgba(255, 255, 255, 2.0)'
    ])
    def test_invalid_colors(self, color):
        """Test that invalid colors are rejected."""
        assert is_valid_color(color) is False
    
    def test_hex_color_validation(self):
        """Test hex color validation specifically."""
        assert is_valid_hex_color('#FF5733') is True
        assert is_valid_hex_color('#ff5733') is True
        assert is_valid_hex_color('#123') is True
        assert is_valid_hex_color('#GGG') is False
        assert is_valid_hex_color('FF5733') is False  # Missing #
    
    def test_rgb_color_validation(self):
        """Test RGB color validation."""
        assert is_valid_rgb_color('rgb(255, 0, 0)') is True
        assert is_valid_rgb_color('rgba(255, 0, 0, 0.5)') is True
        assert is_valid_rgb_color('rgb(300, 0, 0)') is False  # Out of range
        assert is_valid_rgb_color('rgba(255, 0, 0, 2)') is False  # Alpha > 1
    
    def test_hsl_color_validation(self):
        """Test HSL color validation."""
        assert is_valid_hsl_color('hsl(360, 100%, 50%)') is True
        assert is_valid_hsl_color('hsla(360, 100%, 50%, 0.5)') is True
        assert is_valid_hsl_color('hsl(400, 100%, 50%)') is False  # Hue > 360
        assert is_valid_hsl_color('hsl(360, 150%, 50%)') is False  # Saturation > 100%
    
    def test_css_named_colors(self):
        """Test CSS named color validation."""
        assert is_valid_css_named_color('red') is True
        assert is_valid_css_named_color('blue') is True
        assert is_valid_css_named_color('tomato') is True
        assert is_valid_css_named_color('notacolor') is False
    
    def test_get_color_examples(self):
        """Test getting color examples."""
        examples = get_color_examples()
        assert isinstance(examples, list)
        assert len(examples) > 0
        # All examples should be valid
        for example in examples:
            assert is_valid_color(example) is True


@pytest.mark.unit
class TestPydanticColorValidation:
    """Test color validation in Pydantic models."""
    
    def test_valid_color_in_create_model(self):
        """Test creating a model with valid colors."""
        valid_data = {
            'slug': 'test-assignment',
            'title': 'Test Assignment',
            'description': 'A test assignment',
            'color': '#FF5733',
            'course_id': 'test-course-id',
            'course_content_kind_id': 'assignment'
        }
        
        # Should not raise validation error
        content_type = CourseContentTypeCreate(**valid_data)
        # Color might be normalized to lowercase
        assert content_type.color.lower() == '#ff5733'
    
    @pytest.mark.parametrize("color", [
        'red', 'rgb(255, 0, 0)', 'hsl(0, 100%, 50%)', '#FF0000'
    ])
    def test_different_color_formats(self, color):
        """Test different valid color formats in Pydantic model."""
        valid_data = {
            'slug': 'test-assignment',
            'title': 'Test Assignment',
            'description': 'A test assignment',
            'color': color,
            'course_id': 'test-course-id',
            'course_content_kind_id': 'assignment'
        }
        
        content_type = CourseContentTypeCreate(**valid_data)
        # For hex colors, they might be normalized to lowercase
        if color.startswith('#'):
            assert content_type.color.lower() == color.lower()
        else:
            assert content_type.color == color
    
    @pytest.mark.parametrize("color", [
        'invalid-color', '#GGG', 'rgb(300, 300, 300)'
    ])
    def test_invalid_colors_rejected(self, color):
        """Test that invalid colors are rejected by Pydantic model."""
        invalid_data = {
            'slug': 'test-assignment',
            'title': 'Test Assignment',
            'description': 'A test assignment',
            'color': color,
            'course_id': 'test-course-id',
            'course_content_kind_id': 'assignment'
        }
        
        with pytest.raises(ValueError):
            CourseContentTypeCreate(**invalid_data)
    
    def test_update_model_color_validation(self):
        """Test color validation in update model."""
        # Valid color update
        update_data = {'color': '#00FF00'}
        content_update = CourseContentTypeUpdate(**update_data)
        # Color might be normalized to lowercase
        assert content_update.color.lower() == '#00ff00'
        
        # Invalid color update should fail
        with pytest.raises(ValueError):
            CourseContentTypeUpdate(color='notacolor')