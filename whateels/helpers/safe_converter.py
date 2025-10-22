import json

class SafeConverter:
    
    @staticmethod
    def to_int(value, default=0):
        """Safely convert value to int, return default on failure."""
        try:
            if isinstance(value, (int, float)):
                return int(value)
            elif isinstance(value, str) and value.isdigit():
                return int(value)
        except (ValueError, TypeError):
            pass
        return default