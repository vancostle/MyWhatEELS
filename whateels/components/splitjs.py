import panel as pn
import csscompressor, rjsmin

from panel.custom import JSComponent, Child # type: ignore
from whateels.helpers.constants import JS_ROOT, CSS_ROOT

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

        self._left_column_hv = self._find_first_holoviews_pane(self.left_column)
        self._right_column_hv = self._find_first_holoviews_pane(self.right_column)

    def _find_first_holoviews_pane(self, column) -> "pn.pane.HoloViews | None":
        """Find the first HoloViews pane in a given column, if any."""
        if column is not None:
            children = getattr(column, 'objects', None)
            if children is not None:
                for child in children:
                    if isinstance(child, pn.pane.HoloViews):
                        return child
        return None

    def _handle_msg(self, data):
        """Handle messages from JavaScript"""
        
        DRAG_START, DRAGGING, DRAG_END, EXTERNAL_RESIZE = 'drag_start', 'dragging', 'drag_end', 'external_resize'
        EVENTS = [DRAG_START, DRAGGING, DRAG_END, EXTERNAL_RESIZE]
        
        event = data.get('event', '')

        if event not in EVENTS:
            return
        
        if event == DRAG_START:
            self._drag_start_event()
        elif event == DRAGGING or event == EXTERNAL_RESIZE:
            self._dragging_event(widths=data.get('widths', {}))
        elif event == DRAG_END:
            self._drag_end_event()

    def _drag_start_event(self):
        """Handle drag start event.
        HoloViews/Bokeh plots with responsive=True auto-reflow when the container
        resizes, so no manual intervention is needed during drag.
        """
        pass

    def _dragging_event(self, widths: dict):
        """Handle dragging event.
        Bokeh handles responsive resizing automatically — no pixel-width push needed.
        """
        pass

    def _drag_end_event(self):
        """Handle drag end event.
        No cleanup needed; Bokeh restores to container size automatically.
        """
        pass

    def _external_resize_event(self, widths: dict):
        """Handle external resize event"""
        self._drag_start_event()
        self._dragging_event(widths=widths)
        self._drag_end_event()