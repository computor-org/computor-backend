"""
Color validation utilities for HTML/CSS colors.
"""
import re
from typing import Optional


# CSS named colors (subset of commonly used colors)
CSS_NAMED_COLORS = {
    # Basic colors
    'red', 'green', 'blue', 'yellow', 'orange', 'purple', 'pink', 'brown',
    'black', 'white', 'gray', 'grey', 'cyan', 'magenta', 'lime', 'maroon',
    'navy', 'olive', 'silver', 'teal', 'aqua', 'fuchsia',
    
    # Extended colors
    'aliceblue', 'antiquewhite', 'aquamarine', 'azure', 'beige', 'bisque',
    'blanchedalmond', 'blueviolet', 'burlywood', 'cadetblue', 'chartreuse',
    'chocolate', 'coral', 'cornflowerblue', 'cornsilk', 'crimson', 'darkblue',
    'darkcyan', 'darkgoldenrod', 'darkgray', 'darkgrey', 'darkgreen',
    'darkkhaki', 'darkmagenta', 'darkolivegreen', 'darkorange', 'darkorchid',
    'darkred', 'darksalmon', 'darkseagreen', 'darkslateblue', 'darkslategray',
    'darkslategrey', 'darkturquoise', 'darkviolet', 'deeppink', 'deepskyblue',
    'dimgray', 'dimgrey', 'dodgerblue', 'firebrick', 'floralwhite',
    'forestgreen', 'gainsboro', 'ghostwhite', 'gold', 'goldenrod',
    'greenyellow', 'honeydew', 'hotpink', 'indianred', 'indigo', 'ivory',
    'khaki', 'lavender', 'lavenderblush', 'lawngreen', 'lemonchiffon',
    'lightblue', 'lightcoral', 'lightcyan', 'lightgoldenrodyellow',
    'lightgray', 'lightgrey', 'lightgreen', 'lightpink', 'lightsalmon',
    'lightseagreen', 'lightskyblue', 'lightslategray', 'lightslategrey',
    'lightsteelblue', 'lightyellow', 'limegreen', 'linen', 'mediumaquamarine',
    'mediumblue', 'mediumorchid', 'mediumpurple', 'mediumseagreen',
    'mediumslateblue', 'mediumspringgreen', 'mediumturquoise',
    'mediumvioletred', 'midnightblue', 'mintcream', 'mistyrose', 'moccasin',
    'navajowhite', 'oldlace', 'olivedrab', 'orangered', 'orchid',
    'palegoldenrod', 'palegreen', 'paleturquoise', 'palevioletred',
    'papayawhip', 'peachpuff', 'peru', 'plum', 'powderblue', 'rosybrown',
    'royalblue', 'saddlebrown', 'salmon', 'sandybrown', 'seagreen',
    'seashell', 'sienna', 'skyblue', 'slateblue', 'slategray', 'slategrey',
    'snow', 'springgreen', 'steelblue', 'tan', 'thistle', 'tomato',
    'turquoise', 'violet', 'wheat', 'whitesmoke', 'yellowgreen',
    
    # Tailwind CSS colors (commonly used)
    'amber', 'emerald', 'sky', 'rose', 'slate', 'stone', 'zinc', 'neutral'
}


def is_valid_hex_color(color: str) -> bool:
    """
    Check if a string is a valid hex color.
    
    Accepts formats:
    - #RGB (3 digits)
    - #RRGGBB (6 digits)
    - #RGBA (4 digits)
    - #RRGGBBAA (8 digits)
    """
    if not color.startswith('#'):
        return False
    
    hex_part = color[1:]
    if len(hex_part) not in [3, 4, 6, 8]:
        return False
    
    return re.match(r'^[0-9a-fA-F]+$', hex_part) is not None


def is_valid_rgb_color(color: str) -> bool:
    """
    Check if a string is a valid RGB/RGBA color.
    
    Accepts formats:
    - rgb(r, g, b)
    - rgba(r, g, b, a)
    """
    # RGB pattern: rgb(num, num, num)
    rgb_pattern = r'^rgb\s*\(\s*([0-9]{1,3})\s*,\s*([0-9]{1,3})\s*,\s*([0-9]{1,3})\s*\)$'
    
    # RGBA pattern: rgba(num, num, num, alpha)
    rgba_pattern = r'^rgba\s*\(\s*([0-9]{1,3})\s*,\s*([0-9]{1,3})\s*,\s*([0-9]{1,3})\s*,\s*([0-9]*\.?[0-9]+)\s*\)$'
    
    color_lower = color.lower().strip()
    
    if rgb_match := re.match(rgb_pattern, color_lower):
        # Check if RGB values are in valid range (0-255)
        r, g, b = map(int, rgb_match.groups())
        return all(0 <= val <= 255 for val in [r, g, b])
    
    if rgba_match := re.match(rgba_pattern, color_lower):
        # Check if RGB values are in valid range (0-255) and alpha is 0-1
        r, g, b, a = rgba_match.groups()
        r, g, b = map(int, [r, g, b])
        a = float(a)
        return all(0 <= val <= 255 for val in [r, g, b]) and 0 <= a <= 1
    
    return False


def is_valid_hsl_color(color: str) -> bool:
    """
    Check if a string is a valid HSL/HSLA color.
    
    Accepts formats:
    - hsl(h, s%, l%)
    - hsla(h, s%, l%, a)
    """
    # HSL pattern: hsl(hue, saturation%, lightness%)
    hsl_pattern = r'^hsl\s*\(\s*([0-9]+)\s*,\s*([0-9]+)%\s*,\s*([0-9]+)%\s*\)$'
    
    # HSLA pattern: hsla(hue, saturation%, lightness%, alpha)
    hsla_pattern = r'^hsla\s*\(\s*([0-9]+)\s*,\s*([0-9]+)%\s*,\s*([0-9]+)%\s*,\s*([0-9]*\.?[0-9]+)\s*\)$'
    
    color_lower = color.lower().strip()
    
    if hsl_match := re.match(hsl_pattern, color_lower):
        # Check if HSL values are in valid range
        h, s, l = map(int, hsl_match.groups())
        return 0 <= h <= 360 and 0 <= s <= 100 and 0 <= l <= 100
    
    if hsla_match := re.match(hsla_pattern, color_lower):
        # Check if HSL values are in valid range and alpha is 0-1
        h, s, l, a = hsla_match.groups()
        h, s, l = map(int, [h, s, l])
        a = float(a)
        return 0 <= h <= 360 and 0 <= s <= 100 and 0 <= l <= 100 and 0 <= a <= 1
    
    return False


def is_valid_css_named_color(color: str) -> bool:
    """
    Check if a string is a valid CSS named color.
    """
    return color.lower().strip() in CSS_NAMED_COLORS


def is_valid_color(color: str) -> bool:
    """
    Check if a string is a valid color in any supported format.
    
    Supports:
    - Hex colors: #RGB, #RRGGBB, #RGBA, #RRGGBBAA
    - RGB/RGBA: rgb(r, g, b), rgba(r, g, b, a)
    - HSL/HSLA: hsl(h, s%, l%), hsla(h, s%, l%, a)
    - CSS named colors: red, blue, tomato, etc.
    """
    if not color or not isinstance(color, str):
        return False
    
    color = color.strip()
    if not color:
        return False
    
    return (
        is_valid_hex_color(color) or
        is_valid_rgb_color(color) or
        is_valid_hsl_color(color) or
        is_valid_css_named_color(color)
    )


def validate_color(color: str) -> Optional[str]:
    """
    Validate a color string and return normalized version or None if invalid.
    
    Args:
        color: Color string to validate
    
    Returns:
        Normalized color string if valid, None if invalid
    """
    if not is_valid_color(color):
        return None
    
    color = color.strip()
    
    # Normalize hex colors to lowercase
    if color.startswith('#'):
        return color.lower()
    
    # Normalize named colors to lowercase
    if is_valid_css_named_color(color):
        return color.lower()
    
    # RGB/RGBA and HSL/HSLA are returned as-is (already normalized by regex)
    return color


def get_color_examples() -> list[str]:
    """
    Get a list of example valid colors for documentation/testing.
    """
    return [
        # Hex colors
        '#FF5733', '#ff5733', '#123', '#123456', '#12345678',
        
        # RGB/RGBA
        'rgb(255, 87, 51)', 'rgba(255, 87, 51, 0.8)',
        
        # HSL/HSLA
        'hsl(9, 100%, 60%)', 'hsla(9, 100%, 60%, 0.8)',
        
        # Named colors
        'red', 'blue', 'green', 'tomato', 'lightblue', 'darkslategray',
        'amber', 'emerald', 'sky', 'rose'
    ]