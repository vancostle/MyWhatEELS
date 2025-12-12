import panel as pn
import csscompressor, rjsmin

from panel.custom import JSComponent, Child # type: ignore
from whateels.helpers.constants import JS_ROOT, CSS_ROOT

class SplitJs(JSComponent):
    
    left_column= Child(class_=pn.Column) # type: ignore
    right_column = Child(class_=pn.Column) # type: ignore
    
    _FILE_NAME = "splitjs"

    _JS_PATH = JS_ROOT / (_FILE_NAME + '.js')
    _CSS_PATH = CSS_ROOT / (_FILE_NAME + '.css')

    _JS_FILE = str(open(_JS_PATH, 'r', encoding='utf-8').read())
    _CSS_FILE = str(open(_CSS_PATH, 'r', encoding='utf-8').read())

    _importmap = {
        "imports": {
            "splitjs": "https://esm.sh/split.js@1.6.2"
        }
    }
    _esm = str(rjsmin.jsmin(_JS_FILE))
    _stylesheets = [csscompressor.compress(_CSS_FILE)]
    
class SplitJsWrapper(pn.Column):
    def __init__(self, **params):
        super().__init__(SplitJs(), **params)
        