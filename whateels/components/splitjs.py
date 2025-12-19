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

        self._left_column_plotly = self._find_first_plotly_figure(self.left_column)
        self._right_column_plotly = self._find_first_plotly_figure(self.right_column)
        
        if self._left_column_plotly is None and self._right_column_plotly is None:
            return
        
        self._left_column_plotly_figure = self._extract_figure_in_plotly(self._left_column_plotly)
        self._right_column_plotly_figure = self._extract_figure_in_plotly(self._right_column_plotly)

    def _find_first_plotly_figure(self, column) -> pn.pane.Plotly | None:
        """Find the first Plotly figure in a given column, if any."""
        if self.left_column is not None:
            children = getattr(column, 'objects', None)
            if children is not None:
                for child in children:
                    if isinstance(child, pn.pane.Plotly):
                        return child
        return None
    
    def _handle_msg(self, data):
        """Handle messages from JavaScript"""
        
        DRAG_START, DRAGGING, DRAG_END = 'drag_start', 'dragging', 'drag_end'
        EVENTS = [DRAG_START, DRAGGING, DRAG_END]
        
        event = data.get('event', '')

        if event not in EVENTS:
            return
        
        if event == DRAG_START:
            self._drag_start_event()
        elif event == DRAGGING:
            self._dragging_event(widths=data.get('widths', {}))
        elif event == DRAG_END:
            self._drag_end_event()        

        
    def _drag_start_event(self):
        """Handle drag start event"""
        if self._left_column_plotly is not None:
            self._left_column_plotly.config = {'responsive': False}
            self._left_column_plotly.sizing_mode = 'stretch_height'
        if self._right_column_plotly is not None:
            self._right_column_plotly.config = {'responsive': False}
            self._right_column_plotly.sizing_mode = 'stretch_height'
            
    def _dragging_event(self, widths: dict):
        """Handle dragging event"""
        
        if self._left_column_plotly_figure is not None:
            with self._left_column_plotly_figure.batch_update():
                self._left_column_plotly_figure.update_layout(width=widths.get('left'))
            
        if self._right_column_plotly_figure is not None:
            with self._right_column_plotly_figure.batch_update():
                self._right_column_plotly_figure.update_layout(width=widths.get('right'))
    
    def _drag_end_event(self):
        """Handle drag end event"""
        if self._left_column_plotly is not None:
            self._left_column_plotly.config = {'responsive': True}
            self._left_column_plotly.sizing_mode = 'stretch_both'
        if self._right_column_plotly is not None:
            self._right_column_plotly.config = {'responsive': True}
            self._right_column_plotly.sizing_mode = 'stretch_both'
    
    def _extract_plotly_in_column(self, column) -> "pn.pane.Plotly | None":
        """Extract Plotly figure from a column if it contains a Plotly pane"""
        children = getattr(column, 'objects', None)
        if children is None:
            return None

        for child in children:
            if isinstance(child, pn.pane.Plotly):
                obj = child.object
                if obj is not None and hasattr(obj, "__class__") and obj.__class__.__name__ == "Plotly":
                    try:
                        if isinstance(obj, pn.pane.Plotly):
                            return obj
                    except ImportError:
                        pass
        return None
    
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