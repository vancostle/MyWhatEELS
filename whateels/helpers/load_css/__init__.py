import os
import panel as pn
import csscompressor

class LoadCSS:
    """
    A singleton class to load CSS files into the Panel configuration.
    This ensures CSS files are loaded only once, even if the class is instantiated multiple times.
    """
        
    def __init__(self, css_files=None):
        """
        Initialize the LoadCSS instance.
        Only loads CSS on the first instantiation due to the _css_loaded flag.
        
        Args:
            css_files: None or a list/tuple of CSS file paths (strings)
        
        Raises:
            TypeError: If css_files is not None, list, or tuple
            TypeError: If any item in css_files is not a string
        """
        # Validate css_files parameter using explicit type checking
        if css_files is not None:
            # More explicit type checking using isinstance with type objects
            if not isinstance(css_files, (list, tuple)):
                actual_type = type(css_files).__name__
                raise TypeError(f"css_files must be None, list, or tuple; got {actual_type}")
            
            # Check that all items are strings
            for i, css_file in enumerate(css_files):
                if not isinstance(css_file, str):
                    raise TypeError(f"css_files[{i}] must be a string, got {type(css_file).__name__}")
        
        self._load_css(css_files)
    
    def _load_css(self, css_files=[]):
        """
        Load CSS files for the application.
        
        Args:
            css_files: List/tuple of CSS file paths, or None to use defaults
        """
        READ_MODE = "r"
        ENCODING = "utf-8"
        ERROR_MESSAGE = "❌ Error loading CSS file"
        WARNING_MESSAGE = "⚠️ CSS file not found"
        NO_CSS_LOADED_MESSAGE = "No CSS files loaded."
        
        if len(css_files) == 0:
            raise ValueError(NO_CSS_LOADED_MESSAGE)
        
        for css_file in css_files:
            try:
                if os.path.exists(css_file):
                    with open(css_file, READ_MODE, encoding=ENCODING) as f:
                        min_css = csscompressor.compress(f.read())
                        pn.config.raw_css.append(min_css)
                else:
                    print(f"{WARNING_MESSAGE}: {css_file}")
            except Exception as e:
                print(f"{ERROR_MESSAGE} {css_file}: {e}")