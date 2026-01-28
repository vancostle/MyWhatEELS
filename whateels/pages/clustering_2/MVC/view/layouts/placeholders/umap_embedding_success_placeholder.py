import panel as pn

# Inject raw CSS for this component
_raw_css = """
.umap-embedding-success-placeholder {
    background-color: #f0fff4;
    box-shadow: 0px 0px 5px #d8d8d8;
    margin: 0 0 10px 0;
    opacity: 0;
    overflow: hidden;
    aspect-ratio: 1;
}

.umap-embedding-success-placeholder.animated {
    animation: success-bounce-fadein 0.6s cubic-bezier(.68,-0.55,.27,1.55) 0s forwards;
}

@keyframes success-bounce-fadein {
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

class UmapEmbeddingSuccessPlaceholder(pn.Column):

    def __init__(self, min_dist, n_neighbors, delay:float=0, **kwargs):
        # Build styles with animation delay
        styles = {
            'border': '2px solid #10b981',
            'padding': '20px',
            'border-radius': '5px',
            'display': 'flex',
            'flex-direction': 'column',
            'justify-content': 'center',
            'align-items': 'center',
            'animation-delay': f'{delay}s'
        }
        
        # Success indicator with checkmark
        success_icon = pn.pane.HTML(
            """
            <div style="text-align: center;">
                <svg width="60" height="60" viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
                    <polyline points="22 4 12 14.01 9 11.01"></polyline>
                </svg>
            </div>
            """,
            sizing_mode='stretch_width',
            margin=0
        )
        
        super().__init__(
            pn.Row(
                success_icon,
                sizing_mode='stretch_width',
                styles={'justify-content': 'center'}
            ),
            pn.pane.Markdown(
                f"### ✓ Calculation Complete",
                align='center',
                margin=(10, 0, 5, 0),
                styles={'color': '#10b981'}
            ),
            pn.pane.Markdown(
                f"min_dist={min_dist}, n_neighbors={n_neighbors}",
                align='center',
                margin=0,
                styles={'color': '#6b7280', 'font-size': '12px'}
            ),
            align='center',
            css_classes=["umap-embedding-success-placeholder", "animated"],
            styles=styles,
            **kwargs
        )
