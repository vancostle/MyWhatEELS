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

    Dragging writes ``flex`` on the two sibling panes from the browser. Browser
    movement is grouped per animation frame, with Bokeh invalidated at most
    every 50 ms. An optional ratio pane is resized directly on its browser-side
    Bokeh model during the gesture and only its final geometry is reported to
    Python. On release, pending intermediate frames are discarded and the last
    pointer position is committed. Pane overflow is clipped only for the
    gesture, preventing stale canvases from painting across the separator, and
    restored after the final pass. No pane is reparented and no synthetic
    resize event is emitted.

    The row and its two panes are located through the marker classes below,
    which callers must apply via ``css_classes``.
    """

    #: Applied by the caller to the ``pn.Row`` that owns this gutter.
    ROW_CSS_CLASS = "whateels-split-row"
    #: Applied by the caller to both panes, in visual left-to-right order.
    PANE_CSS_CLASS = "whateels-split-pane"
    #: Marks the Bokeh model that may be resized locally during a drag.
    RATIO_PANE_CSS_CLASS = "whateels-ratio-pane"
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
        if self._ratio_pane is not None:
            css_classes = list(self._ratio_pane.css_classes or [])
            if self.RATIO_PANE_CSS_CLASS not in css_classes:
                self._ratio_pane.css_classes = [
                    *css_classes,
                    self.RATIO_PANE_CSS_CLASS,
                ]
        #: Last box the browser reported, so a later ``pane_ratio`` change can
        #: re-fit at once instead of waiting for the next drag or window resize.
        self._last_box: tuple[float, float] | None = None
        params.setdefault('width', self._DEFAULT_WIDTH)
        params.setdefault('sizing_mode', 'stretch_height')
        params.setdefault('margin', 0)
        super().__init__(**params)
        self.param.watch(self._on_pane_ratio_changed, 'pane_ratio')

    def _on_pane_ratio_changed(self, event) -> None:
        """Re-fit when the spatial shape changes under a pane already measured.

        Switching to the energy map or to a clustering map with a different
        shape only changes the ratio; without this the pane would keep the box
        computed for the previous shape until the user happened to drag again.
        """
        if self._last_box is None:
            return
        self._apply_pane_ratio(*self._last_box)

    def _handle_msg(self, data):
        """Persist ``ratio_pane`` from the final box measured by the browser.

        During dragging JavaScript changes the actual browser-side Bokeh model,
        not disposable DOM styles. This final Python update makes that last size
        durable for later ratio changes and server-driven plot replacement.
        """
        if not isinstance(data, dict):
            return
        try:
            width = float(data.get('width') or 0.0)
            height = float(data.get('height') or 0.0)
        except (TypeError, ValueError):
            return
        if width > 0 and height > 0:
            self._last_box = (width, height)
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

        # In fixed sizing mode Bokeh derives the CSS box directly from width and
        # height; duplicating them into min/max constraints adds four property
        # patches without changing the box. Batch the three required values so
        # Panel also invokes its synchronisation watcher only once.
        pane.param.update(
            sizing_mode='fixed',
            width=new_width,
            height=new_height,
        )
