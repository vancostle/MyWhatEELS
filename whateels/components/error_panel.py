import param, csscompressor, rjsmin

from panel.custom import JSComponent 
from whateels.helpers.constants import CSS_ROOT, JS_ROOT

class ErrorPanel(JSComponent):
    """
    A class representing an error panel to display error messages.
    """
    _FILE_NAME = "error_panel"

    _JS_PATH = JS_ROOT / (_FILE_NAME + '.js')
    _CSS_PATH = CSS_ROOT / (_FILE_NAME + '.css')
    
    _JS_FILE = str(open(_JS_PATH, 'r', encoding='utf-8').read())
    _CSS_FILE = str(open(_CSS_PATH, 'r', encoding='utf-8').read())

    _esm = rjsmin.jsmin(_JS_FILE)
    _stylesheets = [csscompressor.compress(_CSS_FILE)]

    message = param.String(default="An error has occurred.")

    def __init__(self, message: str = "An error has occurred.", **params):
        super().__init__(message=message, **params)