import panel as pn

# Inject raw CSS for this component
_raw_css = """
.umap-embedding-placeholder {
    background-color: #fafaff;
    box-shadow: 0px 0px 5px #d8d8d8;
    margin: 0 0 10px 0;
    opacity: 0;
    overflow: hidden;
}

.umap-embedding-placeholder.animated {
    animation: dataset-info-bounce-fadein 0.6s cubic-bezier(.68,-0.55,.27,1.55) 0s forwards;
}

@keyframes dataset-info-bounce-fadein {
    0% {
        opacity: 0;
        transform: scale(0.95);
    }
    60% {
        opacity: 1;
        transform: scale(1.05);
    }
    80% {
        transform: scale(0.98);
    }
    100% {
        opacity: 1;
        transform: scale(1);
    }
}
"""

if _raw_css not in pn.config.raw_css: # type: ignore
    pn.config.raw_css.append(_raw_css) # type: ignore

class UmapEmbeddingPlaceholder(pn.Column):

    def __init__(self, min_dist, n_neighbors, delay:float=0, **kwargs):
        # Build styles with animation delay
        styles = {
            'border': '1px solid #ccc',
            'padding': '20px',
            'border-radius': '5px',
            'display': 'flex',
            'flex-direction': 'column',
            'justify-content': 'center',
            'align-items': 'center',
            'animation-delay': f'{delay}s'
        }
        
        super().__init__(
            pn.Row(
                pn.indicators.LoadingSpinner(value=True, size=50),
                sizing_mode='stretch_width',
                styles={'justify-content': 'center'}
            ),
            pn.pane.Markdown(
                f"min_dist={min_dist}, n_neighbors={n_neighbors}",
                align='center',
            ),
            align='center',
            sizing_mode='stretch_width',
            css_classes=["umap-embedding-placeholder", "animated"],
            styles=styles,
            **kwargs
        )
            