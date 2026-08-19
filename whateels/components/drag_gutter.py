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

    def __init__(self, **params):
        params.setdefault('width', self._DEFAULT_WIDTH)
        params.setdefault('sizing_mode', 'stretch_height')
        params.setdefault('margin', 0)
        super().__init__(**params)
