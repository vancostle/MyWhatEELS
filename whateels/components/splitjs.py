import panel as pn
import csscompressor, rjsmin

from panel.custom import JSComponent, Child # type: ignore
from whateels.helpers.constants import JS_ROOT, CSS_ROOT
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    import plotly.express as px

class SplitJs(JSComponent):
    
    left_column = Child(class_=pn.Column) # type: ignore
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

    def __init__(self, figure, **params):
        super().__init__(**params)
        self.figure = figure
    
    def _handle_msg(self, data):
        """Handle messages from JavaScript"""
        if data.get('event') == 'drag_end':
            sizes = data.get('sizes', [])
            widths = data.get('widths', {})
            print(f"Drag ended! Sizes: {sizes}%, Widths: left={widths.get('left')}px, right={widths.get('right')}px")
            
            self.figure.update_layout(width=widths.get('left'))