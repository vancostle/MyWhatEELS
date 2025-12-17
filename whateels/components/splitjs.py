import panel as pn
import csscompressor, rjsmin
import plotly.graph_objs as go

from panel.custom import JSComponent, Child # type: ignore
from whateels.helpers.constants import JS_ROOT, CSS_ROOT
# from typing import TYPE_CHECKING
# if TYPE_CHECKING:
#     import plotly.express as px

class SplitJs(JSComponent):
    
    left_column = Child(class_=pn.Column) # type: ignore
    right_column = Child(class_=pn.Column) # type: ignore
        
    _FILE_NAME = "splitjs"

    _JS_PATH = JS_ROOT / (_FILE_NAME + '.js')
    _CSS_PATH = CSS_ROOT / (_FILE_NAME + '.css')

    _JS_FILE = str(open(_JS_PATH, 'r', encoding='utf-8').read())
    _CSS_FILE = str(open(_CSS_PATH, 'r', encoding='utf-8').read())

    # Load Split.js library - remove export statement and make it a const
    _SPLITJS_LIB_PATH = JS_ROOT / 'splitjs-lib.js'
    _SPLITJS_LIB = str(open(_SPLITJS_LIB_PATH, 'r', encoding='utf-8').read())
    # Remove the ES module export and wrap in const
    _SPLITJS_LIB_INLINE = _SPLITJS_LIB.replace('export default Split;', 'const SplitLibrary = Split;')
    
    # Combine: library first, then our code
    _COMBINED_JS = _SPLITJS_LIB_INLINE + '\n\n' + _JS_FILE
    
    _esm = str(rjsmin.jsmin(_COMBINED_JS))
    _stylesheets = [csscompressor.compress(_CSS_FILE)]

    def __init__(self, **params):
        super().__init__(**params)
        
        if hasattr(self.left_column, 'styles') and isinstance(self.left_column, pn.Column):
            self.left_column.styles = {'overflow-x': 'hidden'}
        
        if hasattr(self.right_column, 'styles') and isinstance(self.right_column, pn.Column):
            self.right_column.styles = {'overflow-x': 'hidden'}
            
        left_column_children = getattr(self.left_column, 'objects', None)
        left_column_contains_plotly = self._some_child_is_plotly(left_column_children)
        
        figure = None
        if left_column_contains_plotly and left_column_children is not None:
            for child in left_column_children:
                plotly_figure = self._extract_figure_in_plotly(child)
                if plotly_figure is not None:
                    figure = plotly_figure
                    break
        
        self._left_column_figure = figure
        
        right_column_children = getattr(self.right_column, 'objects', None)
        right_column_contains_plotly = self._some_child_is_plotly(right_column_children)
        
        figure = None
        if right_column_contains_plotly and right_column_children is not None:
            for child in right_column_children:
                plotly_figure = self._extract_figure_in_plotly(child)
                if plotly_figure is not None:
                    figure = plotly_figure
                    break
                
        self._right_column_figure = figure
    
    def _handle_msg(self, data):
        """Handle messages from JavaScript"""
        
        widths = data.get('widths', {})
        
        if self._left_column_figure is not None:
            with self._left_column_figure.batch_update():
                self._left_column_figure.update_layout(width=widths.get('left'))
            
        if self._right_column_figure is not None:
            with self._right_column_figure.batch_update():
                self._right_column_figure.update_layout(width=widths.get('right'))
            
    def _some_child_is_plotly(self, children) -> bool:
        """Check if any of the children is a Plotly pane"""
        if children is None:
            return False

        for child in children:
            if isinstance(child, pn.pane.Plotly):
                return True
    
        return False
    
    def _extract_figure_in_plotly(self, child) -> "go.Figure | None":
        """Extract Plotly figure from a child if it is a Plotly pane"""
        if isinstance(child, pn.pane.Plotly):
            obj = child.object
            if obj is not None and hasattr(obj, "__class__") and obj.__class__.__name__ == "Figure":
                try:
                    if isinstance(obj, go.Figure):
                        return obj
                except ImportError:
                    pass
        return None