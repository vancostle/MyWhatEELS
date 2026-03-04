import panel as pn, param

class _UmapEmbeddingParams(param.Parameterized):
    """ Parameters for managing the state of UMAP embedding placeholders, including loading and disappear states. """
    is_loading = param.Boolean(default=True, doc="Whether the UMAP embedding is currently loading.")
    disappear = param.Boolean(default=False, doc="Whether the placeholder should animate disappear.")

class UmapEmbeddingPlaceholder(pn.Column):
    """ A placeholder component for UMAP embeddings that shows a loading spinner and title, with support for animated appearance and disappearance. """

    def __init__(self, min_dist, n_neighbors, delay:float=0, is_loading: bool = False, **kwargs):
        self._params = _UmapEmbeddingParams(is_loading=is_loading)
        self._params.param.watch(self._update_loading_state, 'is_loading')
        self._params.param.watch(self._update_disappear_state, 'disappear')

        # Build styles with animation delay
        styles = {
            'border-radius': '5px',
            'display': 'flex',
            'flex-direction': 'column',
            'justify-content': 'center',
            'align-items': 'center',
            'animation-delay': f'{delay}s',
            'box-sizing': 'border-box',
            'height': '100%',
        }
        
        self._loading_spinner = pn.indicators.LoadingSpinner(
            value=True, 
            size=50,
            color="success" if bool(self._params.is_loading) else "primary"
        )
        
        indicator = pn.Row(
            self._loading_spinner,
            sizing_mode='stretch_width',
            margin=0,
            styles={'justify-content': 'center'}
        )

        self._title = pn.pane.Markdown(
            f"### {'Calculating UMAP embedding...' if bool(self._params.is_loading) else 'Waiting...'}",
            align='center', 
            margin=0,
            styles={'text-align': 'center'}
        )            
        
        super().__init__(
            indicator,
            self._title,
            pn.pane.Markdown(
                f"min_dist={min_dist}, n_neighbors={n_neighbors}",
                align='center',
                margin=0
            ),
            align='center',
            css_classes=["umap-embedding-placeholder", "animated-in"],
            styles=styles,
            **kwargs
        )
        
    @property
    def is_loading(self) -> bool:
        return bool(self._params.is_loading)
    
    @is_loading.setter
    def is_loading(self, value: bool):
        self._params.is_loading = value
        
    def _update_loading_state(self, event):
        is_loading = bool(event.new)
        self._loading_spinner.color = "success" if is_loading else "primary"
        self._title.object = f"### {'Calculating UMAP embedding...' if is_loading else 'Waiting...'}"

    def _update_disappear_state(self, event):
        if event.new:
            # Remove animated-in class and add animated-out to avoid conflicts
            current_classes = self.css_classes or []
            new_classes = [c for c in current_classes if c != "animated-in"]
            if "animated-out" not in new_classes:
                new_classes.append("animated-out")
            # Reassign to trigger Panel re-render
            self.css_classes = new_classes

    def disappear(self, delay: float = 0):
        """Trigger a fade-out animation (opacity 0), but do not hide/remove from layout. Optionally stagger with delay."""
        if (self.styles is None):
            self.styles = {}
        self.styles = {**self.styles, 'opacity': '1', 'animation-delay': f'{delay}s'}
        self._params.disappear = True