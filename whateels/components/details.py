import panel as pn
import param
import csscompressor, rjsmin

from panel.custom import JSComponent, Child
from whateels.helpers.constants import JS_ROOT, CSS_ROOT

# TODO - This component works but actually is not being used anywhere yet. Implement it or remove it with its css and js files.
class DetailsJS(JSComponent):

    title = Child(class_=pn.pane.Markdown)
    content = Child(class_=pn.Column)
    expanded = param.Boolean(default=False)
    
    value = param.Parameter()
    isComponentLoaded = param.Boolean(default=False)
    
    _FILE_NAME = "details"
    
    _JS_PATH = JS_ROOT / (_FILE_NAME + '.js')
    _CSS_PATH = CSS_ROOT / (_FILE_NAME + '.css')
    
    _JS_FILE = str(open(_JS_PATH, 'r', encoding='utf-8').read())
    _CSS_FILE = str(open(_CSS_PATH, 'r', encoding='utf-8').read())

    _esm = rjsmin.jsmin(_JS_FILE)
    _stylesheets = [csscompressor.compress(_CSS_FILE)]
    
    def __init__(self, **params):
        super().__init__(**params)
    
class Details(pn.Column):
    """ A wrapper around the Details component to simplify its creation. """
    
    def __init__(
        self, 
        title: str = "Details Title", 
        content = None, 
        expanded: bool = False,
        **params
    ):        
        if content is None:
            content = pn.Column(
                pn.pane.Markdown("Details content goes here.", sizing_mode="stretch_both"),
                sizing_mode="stretch_both"
            )
        
        self._loading_panel = pn.Column(
            pn.pane.Markdown(
                f"{title}", 
                sizing_mode="stretch_both", 
                styles={'margin': '0px', 'padding': '0 0 0 13px', 'color': 'white'}
            ),
            sizing_mode="stretch_both",
            styles={
                'display': 'flex', 
                'justify-content': 'center', 
                'align-items': 'center',
                'width': '100%',
                'height': '100%',
                'min-height': '100%',
                'background-color': 'var(--header-background)',
                'z-index': '10',
                'border-radius': '4px',
                'position': 'absolute',
                'inset': '0',
            }
        )
            
        self._details = DetailsJS(
            title=pn.pane.Markdown(f"{title}", sizing_mode="stretch_both"),
            content=content,
            expanded=expanded,
            sizing_mode="stretch_both",
            styles={'pointer-events': 'none', 'opacity': '0', 'position': 'absolute', 'inset': '0'},  # Initially disable interaction
        )
                
        super().__init__(
            self._loading_panel,
            self._details,
            **params
        )
        
        self.styles={'position': 'relative'}
                
        # Watch for value changes (header height) to set wrapper height
        self._details.param.watch(self._update_height, 'value')
        self._details.param.watch(self._component_loaded, 'isComponentLoaded')
    
    def _update_height(self, event):
        """Update wrapper height when header height is received from JS."""
        if event.new is not None:
            self.height = event.new
            self.styles={'max-height': f'{event.new}px'}
            
    def _component_loaded(self, event):
        """Handle component loaded event."""        
        self._details.styles={'pointer-events': 'auto', 'opacity': '1'}  # Enable interaction
        self._loading_panel.styles={'display': 'none'}  # Hide loading panel
