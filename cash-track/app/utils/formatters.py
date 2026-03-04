"""
Utility functions for formatting and data processing
"""


def format_number(value):
    """Format number with dots as thousand separators"""
    return '{:,.0f}'.format(value).replace(',', '.')
