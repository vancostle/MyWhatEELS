from panel.custom import JSComponent, Child
import csscompressor, rjsmin
import param
import csscompressor
from whateels.helpers.constants import CSS_ROOT, JS_ROOT

class UploadedFile(JSComponent):
    """
    A class representing an uploaded file with its name.
    """
    _FILE_NAME = "uploaded_file"

    _JS_PATH = JS_ROOT / (_FILE_NAME + '.js')
    _CSS_PATH = CSS_ROOT / (_FILE_NAME + '.css')
    
    _JS_FILE = str(open(_JS_PATH, 'r', encoding='utf-8').read())
    _CSS_FILE = str(open(_CSS_PATH, 'r', encoding='utf-8').read())

    _esm = rjsmin.jsmin(_JS_FILE)
    _stylesheets = [csscompressor.compress(_CSS_FILE)]

    filename = param.String(default="default.dm3")

    def __init__(self, filename: str = "default.dm3", **params):
        super().__init__(filename=filename, **params)