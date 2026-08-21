import param
import csscompressor, rjsmin

from panel.custom import JSComponent # type: ignore
from whateels.helpers.constants import JS_ROOT, CSS_ROOT


class DragGutter(JSComponent):
    """Draggable separator for a native two-pane ``pn.Row``.

    Unlike :class:`~whateels.components.splitjs.SplitJs`, this component never
    becomes the parent of the panes it resizes. It declares no ``Child``
    parameters and renders only the separator itself, so ``paneA`` and ``paneB``
    stay exactly where Panel/Bokeh mounted them. That is the difference that
    matters in Fitting: a component that reparents its panes leaves Bokeh
    solving the layout of one hierarchy while the browser paints another, and
    every additive result that invalidates the root then detaches axes, titles
    and colour bars from their canvas.

    Dragging writes ``flex`` on the two sibling panes from the browser and
    nothing else. No message travels to Python, no geometry is written from the
    server and no synthetic resize event is emitted, so publishing a run or a
    derived analysis stays as cheap as it is today.

    The row and its two panes are located through the marker classes below,
    which callers must apply via ``css_classes``.
    """

    #: Applied by the caller to the ``pn.Row`` that owns this gutter.
    ROW_CSS_CLASS = "whateels-split-row"
    #: Applied by the caller to both panes, in visual left-to-right order.
    PANE_CSS_CLASS = "whateels-split-pane"
    pane_ratio = param.Number(default=0.0, bounds=(0, None), doc="""
        X/Y ratio the pane passed as ``ratio_pane`` must keep. Zero disables the
        sizing entirely and the gutter only redistributes flex, as before.""")

    min_pane_size = param.Integer(default=160, bounds=(0, None), doc="""
        Smallest width in pixels that dragging may leave on either pane. It is
        clamped to half the available width so that narrow rows stay usable.""")

    _FILE_NAME = "drag_gutter"

    _JS_PATH = JS_ROOT / (_FILE_NAME + '.js')
    _CSS_PATH = CSS_ROOT / (_FILE_NAME + '.css')

    _JS_FILE = str(open(_JS_PATH, 'r', encoding='utf-8').read())
    _CSS_FILE = str(open(_CSS_PATH, 'r', encoding='utf-8').read())

    _esm = str(rjsmin.jsmin(_JS_FILE))
    _stylesheets = [csscompressor.compress(_CSS_FILE)]

    _DEFAULT_WIDTH = 10
    #: Same slack SplitJs keeps, so a rounded box never trips a scrollbar.
    _FIT_MARGIN = 8

    def __init__(self, **params):
        # A plain Python reference, never a ``Child`` parameter: the pane stays
        # where Panel mounted it and this component never becomes its parent.
        # Reparenting is what detached axes and colour bars from their canvas.
        self._ratio_pane = params.pop('ratio_pane', None)
        params.setdefault('width', self._DEFAULT_WIDTH)
        params.setdefault('sizing_mode', 'stretch_height')
        params.setdefault('margin', 0)
        super().__init__(**params)

    def _handle_msg(self, data):
        """Size ``ratio_pane`` from the box the browser just measured.

        The pane is sized here, in Python, and not from the browser, because the
        pane is a Bokeh-managed element: under any responsive sizing mode Bokeh
        rewrites its inline width/height on every layout solve, so styles written
        from JavaScript are overwritten as soon as the next solve runs. Setting
        the *model* is the only instruction Bokeh applies and keeps, which is
        exactly why SplitJs does it this way too.
        """
        if not isinstance(data, dict):
            return
        try:
            width = float(data.get('width') or 0.0)
            height = float(data.get('height') or 0.0)
        except (TypeError, ValueError):
            return
        self._apply_pane_ratio(width, height)

    def _apply_pane_ratio(self, width: float, height: float) -> None:
        """Fit the ratio inside the measured box, height first.

        ``w = min(available_width, available_height * ratio)`` then
        ``h = w / ratio`` - the same fit as
        :meth:`~whateels.components.splitjs.SplitJs._apply_left_plot_pixel_ratio`.
        While the pane is wide enough the image takes the whole height; as soon
        as the width is the binding side the height is given back, so the ratio
        holds through a drag instead of the image being squashed.
        """
        pane = self._ratio_pane
        ratio = float(self.pane_ratio or 0.0)
        if pane is None or ratio <= 0 or width <= 0 or height <= 0:
            return

        max_width = max(1.0, width - self._FIT_MARGIN)
        max_height = max(1.0, height - self._FIT_MARGIN)
        new_width = max(1, int(round(min(max_width, max_height * ratio))))
        new_height = max(1, int(round(new_width / ratio)))

        if (
            pane.width == new_width
            and pane.height == new_height
            and pane.sizing_mode == 'fixed'
        ):
            return

        pane.sizing_mode = 'fixed'
        pane.width = new_width
        pane.height = new_height
        pane.min_width = new_width
        pane.max_width = new_width
        pane.min_height = new_height
        pane.max_height = new_height
