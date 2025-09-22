from whateels.helpers.constants import HTML_ROOT
import minify_html

class Placeholders:
    
    @staticmethod
    def _load_html_template(filename: str) -> str:
        """Load an HTML template from a file"""
        READ_MODE = 'r'
        UTF_8 = 'utf-8'

        with open(filename, READ_MODE, encoding=UTF_8) as f:
            html = f.read()

        minified_html = minify_html.minify(html)

        return minified_html

    NO_FILE_LOADED = _load_html_template(str(HTML_ROOT / "no_file_loaded.html"))
    LOADING_FILE = _load_html_template(str(HTML_ROOT / "loading_file.html"))
    ERROR_FILE = _load_html_template(str(HTML_ROOT / "error_file.html"))