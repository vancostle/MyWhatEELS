import functools
from whateels.helpers.constants import HTML_ROOT

class Placeholders:

    @staticmethod
    def _load_html_template(filename: str) -> str:
        """Load an HTML template from a file"""
        with open(filename, 'r', encoding='utf-8') as f:
            return f.read()

    @functools.cached_property
    def NO_FILE_LOADED(self) -> str:
        return self._load_html_template(str(HTML_ROOT / "no_file_loaded.min.html"))

    @functools.cached_property
    def LOADING_FILE(self) -> str:
        return self._load_html_template(str(HTML_ROOT / "loading_file.min.html"))

    @functools.cached_property
    def ERROR_FILE(self) -> str:
        return self._load_html_template(str(HTML_ROOT / "error_file.min.html"))