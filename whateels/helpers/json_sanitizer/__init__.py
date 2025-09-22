"""
JSON Sanitizer Helper

This module provides utilities to convert Python objects with non-JSON serializable
data types (like NumPy arrays, NaN values, custom objects) into JSON-safe formats.
"""

import json
import numpy as np
from typing import Any


def sanitize_for_json(obj: Any) -> Any:
    """
    Convert all non-JSON serializable objects to JSON-safe formats.
    
    This function recursively processes Python objects and converts problematic
    data types commonly found in scientific data (NumPy arrays, NaN values, 
    custom objects) into JSON-serializable formats.
    
    Args:
        obj: Any Python object to sanitize
        
    Returns:
        JSON-serializable version of the input object
        
    Examples:
        >>> sanitize_for_json({'data': np.array([1, 2, 3]), 'value': np.nan})
        {'data': [1, 2, 3], 'value': 'NaN'}
        
        >>> sanitize_for_json([1, 2, np.inf, "hello"])
        [1, 2, 'Infinity', 'hello']
    """
    if isinstance(obj, dict):
        return {k: sanitize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [sanitize_for_json(item) for item in obj]
    elif isinstance(obj, (str, int, bool, type(None))):
        # For strings, ensure they don't contain problematic characters
        if isinstance(obj, str):
            try:
                # Test if the string is JSON serializable
                json.dumps(obj)
                return obj
            except (UnicodeDecodeError, UnicodeEncodeError, TypeError):
                # Replace problematic characters with escaped representation
                return repr(obj)
        return obj
    elif isinstance(obj, float):
        # Handle special float values that aren't valid JSON
        if np.isnan(obj):
            return "NaN"
        elif np.isinf(obj):
            return "Infinity" if obj > 0 else "-Infinity"
        else:
            return obj
    elif isinstance(obj, np.ndarray):
        # Convert NumPy arrays to lists, but handle large arrays specially
        if obj.size > 1000:  # Limit very large arrays
            return f"<NumPy Array: shape={obj.shape}, dtype={obj.dtype}, size={obj.size}>"
        return sanitize_for_json(obj.tolist())
    elif isinstance(obj, (np.integer, np.floating)):
        # Convert NumPy scalar types to Python native types
        return sanitize_for_json(obj.item())
    elif isinstance(obj, (bytes, bytearray)):
        # Handle binary data
        return f"<Binary data: {len(obj)} bytes>"
    else:
        # Convert everything else to a safe string representation
        try:
            return str(obj)
        except Exception:
            return f"<{type(obj).__name__}>"


def is_json_serializable(obj: Any) -> bool:
    """
    Test if an object is JSON serializable without modification.
    
    Args:
        obj: Object to test
        
    Returns:
        True if object can be JSON serialized as-is, False otherwise
    """
    try:
        json.dumps(obj)
        return True
    except (TypeError, ValueError, OverflowError):
        return False