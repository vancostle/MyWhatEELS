import panel as pn
import param
import csscompressor, rjsmin

from panel.custom import JSComponent, Child
from whateels.helpers.constants import JS_ROOT, CSS_ROOT

class Details(JSComponent):

    title = Child(class_=pn.pane.Markdown)
    content = Child(class_=pn.Column)
    expanded = param.Boolean(default=False)    
    _FILE_NAME = "details"
    
    _JS_PATH = JS_ROOT / (_FILE_NAME + '.js')
    _CSS_PATH = CSS_ROOT / (_FILE_NAME + '.css')
    
    _JS_FILE = str(open(_JS_PATH, 'r', encoding='utf-8').read())
    _CSS_FILE = str(open(_CSS_PATH, 'r', encoding='utf-8').read())

    _esm = rjsmin.jsmin(_JS_FILE)
    _stylesheets = [csscompressor.compress(_CSS_FILE)]