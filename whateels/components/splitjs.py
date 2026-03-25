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

        self._left_column_hv : pn.pane.HoloViews = self._find_first_holoviews_pane(self.left_column)
        self._right_column_hv : pn.pane.HoloViews = self._find_first_holoviews_pane(self.right_column)

    def _find_first_holoviews_pane(self, column) -> "pn.pane.HoloViews":
        """Find the first HoloViews pane in a given column, if any."""
        if column is None:
            raise ValueError("Column cannot be None when searching for HoloViews panes.")

        children = getattr(column, 'objects', None)
        if children is None:
            raise ValueError("Column does not have 'objects' attribute to search for HoloViews panes.")
    
        for child in children:
            if isinstance(child, pn.pane.HoloViews):
                return child
        raise ValueError("No HoloViews pane found in the given column.")

    def _handle_msg(self, data):
        """Handle messages from JavaScript"""
        
        DRAG_START, DRAGGING, DRAG_END, EXTERNAL_RESIZE = 'drag_start', 'dragging', 'drag_end', 'external_resize'
        EVENTS = [DRAG_START, DRAGGING, DRAG_END, EXTERNAL_RESIZE]
        
        event = data.get('event', '')

        if event not in EVENTS:
            return

        widths = data.get('widths', {}) or {}
        heights = data.get('heights', {}) or {}
        
        if event == DRAG_START:
            self._drag_start_event()
        elif event == DRAGGING or event == EXTERNAL_RESIZE:
            self._dragging_event(widths=widths, heights=heights)
        elif event == DRAG_END:
            self._drag_end_event(widths=widths, heights=heights)

    def _drag_start_event(self):
        """Handle drag start event.
        HoloViews/Bokeh plots with responsive=True auto-reflow when the container
        resizes, so no manual intervention is needed during drag.
        """
        pass # No action needed at drag start since Bokeh handles resizing automatically

    def _dragging_event(self, widths: dict, heights: dict):
        """Handle dragging event.
        For paneA image plots, enforce fixed pixel ratio by recalculating both
        frame width and frame height from current split panel dimensions.
        """
        self._apply_left_plot_pixel_ratio(widths=widths, heights=heights)

    def _drag_end_event(self, widths: dict, heights: dict):
        """Handle drag end event.
        No cleanup needed; Bokeh restores to container size automatically.
        """
        self._apply_left_plot_pixel_ratio(widths=widths, heights=heights)
        self.force_holoviews_resize()  # Final refresh to ensure everything is up-to-date after drag

    def _external_resize_event(self, widths: dict):
        """ Handle external resize event (e.g., window resize).
        This can be triggered by JavaScript when the window is resized, allowing us to refresh HoloViews panes if needed.
        """
        pass # No action needed during external resize since Bokeh handles resizing automatically, but we could call force_holoviews_resize() if we find it necessary
        
    def force_holoviews_resize(self):
        """Force a refresh on HoloViews panes in both columns."""
        if self._left_column_hv is not None and isinstance(self._left_column_hv, pn.pane.HoloViews):
            self._left_column_hv.object = self._left_column_hv.object
        if self._right_column_hv is not None and isinstance(self._right_column_hv, pn.pane.HoloViews):
            self._right_column_hv.object = self._right_column_hv.object

    def _apply_left_plot_pixel_ratio(self, widths: dict, heights: dict):
        """Resize paneA by fitting width/height simultaneously while preserving X/Y ratio."""
        left_column : pn.pane.HoloViews = self._left_column_hv

        try:
            ratio = float(getattr(left_column, '_splitjs_xy_ratio', 1.0))
        except (ValueError, TypeError):
            ratio = 1.0

        if ratio <= 0:
            ratio = 1.0

        left_w = float(widths.get('left', 0) or 0)
        left_h = float(heights.get('left', 0) or 0)
        if left_w <= 0 or left_h <= 0:
            return

        # Keep a small safety margin to avoid scrollbars from gutter/padding jitter.
        max_w = max(1.0, left_w - 8.0)
        max_h = max(1.0, left_h - 8.0)

        width_from_height = max_h * ratio
        target_w = min(max_w, width_from_height)
        target_h = target_w / ratio

        new_w = max(1, int(round(target_w)))
        new_h = max(1, int(round(target_h)))

        if left_column.width == new_w and left_column.height == new_h and left_column.sizing_mode == 'fixed':
            return

        left_column.sizing_mode = 'fixed'
        left_column.width = new_w
        left_column.height = new_h