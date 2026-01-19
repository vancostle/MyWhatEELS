"""Visualization methods for UMAP_HDBSCAN analysis."""

import numpy as np
import holoviews as hv
import xarray as xr
from bokeh.io import show
from bokeh.layouts import row

from .colormaps import get_tinted_grey_cmap, add_wavelength_axis


def plot_hdbscan_map_intensities(data, clustering, channel=None, cmap='cubehelix'):
    """
    Crear mapas ponderados por intensidad para cada cluster usando holoviews/bokeh.
    Si channel=None, usa la suma total del espectro por píxel. Si channel es un índice, usa ese canal.
    Visualiza los mapas con holoviews/bokeh.
    
    Parameters:
    -----------
    data : np.ndarray
        3D spectral data
    clustering : np.ndarray
        2D array of cluster labels
    channel : int, optional
        Energy channel to use (None = sum all channels)
    cmap : str
        Colormap name
    """
    shape = clustering.shape
    flat_clustering = clustering.reshape(-1)
    
    if channel is None:
        # Intensidad integrada (suma del espectro)
        intensities = data.sum(axis=-1).reshape(-1)
    else:
        # Intensidad en un canal específico
        intensities = data[..., channel].reshape(-1)
        
    unique_labels = np.unique(flat_clustering)
    
    for label in unique_labels:
        if label == -1:
            continue  # Omitir outliers
            
        mask = (flat_clustering == label)
        intensity_map = np.zeros_like(flat_clustering, dtype=float)
        intensity_map[mask] = intensities[mask]
        intensity_map_2d = intensity_map.reshape(shape)
        
        # Calcular rango de valores solo para píxeles del cluster (no-cero)
        cluster_values = intensity_map[mask]
        if len(cluster_values) > 0:
            vmin = cluster_values.min()
            vmax = cluster_values.max()
        else:
            vmin, vmax = 0, 1
        
        # Crear máscara para píxeles fuera del cluster (poner NaN para que no aparezcan en colorbar)
        intensity_map_2d_masked = intensity_map_2d.copy()
        intensity_map_2d_masked[intensity_map_2d == 0] = np.nan
        
        img = hv.Image(
            xr.Dataset(
                {f'Intensidad_Cluster_{label}': (['y', 'x'], intensity_map_2d_masked)},
                coords={'x': np.arange(shape[1]), 'y': np.arange(shape[0])}
            ),
            kdims=['x', 'y']
        ).opts(
            xaxis=None, yaxis=None, colorbar=True, tools=['hover'], toolbar='right',
            invert_yaxis=True, aspect='equal', frame_height=300,
            cmap=cmap,
            clim=(vmin, vmax),
            bgcolor='black',
            title=f'Intensidad integrada - Cluster {label}' if channel is None else f'Intensidad canal {channel} - Cluster {label}'
        )
        show(hv.render(img, backend='bokeh'))


def plot_hdbscan_map_probabilities(clustering, hdbscan_results, norm='log'):
    """
    Visualización soft del clustering usando HDBSCAN.
    Muestra un mapa por cluster con la probabilidad de pertenencia por píxel.
    
    Parameters:
    -----------
    clustering : np.ndarray
        2D array of cluster labels
    hdbscan_results : HDBSCAN object
        HDBSCAN results with probabilities_
    norm : str
        'log' or 'exp' normalization
    """
    probs = hdbscan_results.probabilities_
    labels = hdbscan_results.labels_
    shape = clustering.shape
    probs_2d = probs.reshape(shape)
    labels_2d = labels.reshape(shape)
    
    # Para cada cluster (excepto outlier -1), mostrar mapa de probabilidad
    for idx, label in enumerate(np.unique(labels)):
        if label == -1:
            continue  # Omitir outliers
            
        mask = (labels_2d == label)
        prob_map = np.zeros_like(probs_2d)
        prob_map[mask] = probs_2d[mask]
        
        if norm == 'log':
            prob_map = np.log1p(prob_map)
        elif norm == 'exp':
            prob_map = np.expm1(prob_map)

        img = hv.Image(
            xr.Dataset(
                {f'Probabilidad_Cluster_{label}': (['y', 'x'], prob_map)},
                coords={'x': np.arange(shape[1]), 'y': np.arange(shape[0])}
            ),
            kdims=['x', 'y']
        ).opts(
            xaxis=None, yaxis=None, colorbar=True, tools=['hover'], toolbar='right',
            invert_yaxis=True, aspect='equal', frame_height=300,
            title=f'Probabilidad de pertenencia - Cluster {label}',
            cmap='cubehelix'
        )
        show(hv.render(img, backend='bokeh'))


def plot_hdbscan_map(data, clustering, cmap_obj):
    """
    Plot HDBSCAN clustering map.
    
    Parameters:
    -----------
    data : np.ndarray
        3D spectral data (for shape info)
    clustering : np.ndarray
        2D array of cluster labels
    cmap_obj : CmapObj
        Colormap object with .colors attribute
    """
    img = hv.Image(
        xr.Dataset(
            {'Labels': (['y', 'x'], clustering)},
            coords={'x': np.arange(data.shape[1]),
                   'y': np.arange(data.shape[0])}
        ),
        kdims=['x', 'y']
    ).opts(
        xaxis=None, yaxis=None, colorbar=True, tools=['hover'], toolbar='right',
        invert_yaxis=True, aspect='equal', frame_height=300, cmap=cmap_obj.colors,
        title='HDBSCAN map'
    )
    show(hv.render(img, backend='bokeh'))


def plot_umap_embedding_with_labels(embedding, labels, cmap_obj, min_samp, min_clust):
    """
    Plot UMAP embedding colored by cluster labels.
    
    Parameters:
    -----------
    embedding : np.ndarray
        2D UMAP embedding
    labels : np.ndarray
        Cluster labels
    cmap_obj : CmapObj
        Colormap object
    min_samp : int
        HDBSCAN min_samples parameter
    min_clust : int
        HDBSCAN min_cluster_size parameter
    """
    zers = np.zeros((embedding.shape[0], 3))
    zers[:, :-1] = embedding
    zers[:, -1] = labels
    
    points = hv.Points(zers, vdims=['color']).opts(
        frame_width=650, frame_height=300, toolbar='right', fill_alpha=0.1, bgcolor='black',
        line_alpha=0, line_width=0.15, size=2.5, xaxis=None, yaxis=None, cmap=cmap_obj.colors,
        show_legend=True, color='color', shared_axes=False,
        title=f'UMAP embedding min_samples={min_samp}, min_cluster_size={min_clust}'
    )
    show(hv.render(points, backend='bokeh'))


def plot_mean_spectra_per_cluster(data, e_loss, clustering, cmap_obj):
    """
    Plot the mean spectrum for each cluster as colored curves.
    
    Parameters:
    -----------
    data : np.ndarray
        3D spectral data
    e_loss : np.ndarray
        Energy loss axis
    clustering : np.ndarray
        2D cluster labels
    cmap_obj : CmapObj
        Colormap object
    """
    energy_axis = e_loss
    mean_spectra_overlay = {}
    flat_clustering = clustering.reshape(-1)
    flat_spectra = data.reshape(-1, energy_axis.size)
    
    print('Shapes: flat_clustering', flat_clustering.shape, 'flat_spectra', flat_spectra.shape)
    unique_labels = np.unique(flat_clustering)
    
    for idx, label in enumerate(unique_labels):
        cluster_mask = (flat_clustering == label)
        spectra_cluster = flat_spectra[cluster_mask]
        mean_spectrum = np.mean(spectra_cluster, axis=0)
        
        curve = hv.Curve(
            (energy_axis, mean_spectrum),
            'Eloss',
            f'Intensity (Label {label})'
        ).opts(color=cmap_obj.colors[idx])
        
        mean_spectra_overlay[f'Label_{label}'] = curve

    overlay = hv.NdOverlay(mean_spectra_overlay).opts(
        frame_height=300,
        frame_width=650,
        bgcolor='black',
        legend_cols=False,
        legend_position='right',
        show_grid=True,
        ylabel='Intensity (counts)',
        xlabel='Energy Loss (eV)',
        title='Centroids of HDBSCAN on the UMAP embedding',
        hooks=[add_wavelength_axis]
    )
    show(hv.render(overlay, backend='bokeh'))


def visualize_umap_embedding(min_dist_list, n_neighbors_list, umap_data_dict):
    """
    Visualize multiple UMAP embeddings using holoviews/bokeh.
    
    Parameters:
    -----------
    min_dist_list : list
        List of min_dist values
    n_neighbors_list : list
        List of n_neighbors values
    umap_data_dict : dict
        Dictionary of UMAP mappers
    """
    embeddings_plots = []

    for min_dist in min_dist_list:
        for n_neighbors in n_neighbors_list:
            emb = umap_data_dict['umap_data_{}_{}'.format(min_dist, n_neighbors)].embedding_
            zers = np.zeros((emb.shape[0], 3))
            zers[:, :-1] = emb
            
            points = hv.Points(zers, vdims=['color']).opts(
                frame_width=650,
                frame_height=300,
                toolbar=None,
                fill_alpha=0.1,
                bgcolor='black',
                line_alpha=0,
                line_width=0.15,
                size=2.5,
                xaxis=None,
                yaxis=None,
                show_legend=True,
                color='color',
                shared_axes=False,
                title=('UMAP on masked data, min_dist={}, n_neighbors={}'.format(min_dist, n_neighbors))
            )
            embeddings_plots.append(points)
            
    layout = hv.Layout(embeddings_plots).cols(len(n_neighbors_list))
    show(hv.render(layout, backend='bokeh'))
    print("UMAP embeddings visualized successfully.")


def plot_clusters_overlay(data, clustering, hdbscan_results, labels=None, colors=None, channel=None,
                          max_labels=6, frame_height=300, frame_width=650,
                          colorbar_width=90, colorbar_spacing=0, colorbar_position='right',
                          colorbar_side='left'):
    """
    Superpone varios mapas de intensidad (uno por cluster) en un único plot con estilo
    consistente con los demás plots del core (bgcolor negro, invert_yaxis, aspect='equal').

    Parámetros:
    -----------
    data : np.ndarray
        3D spectral data
    clustering : np.ndarray
        2D cluster labels
    hdbscan_results : HDBSCAN object
        HDBSCAN results
    labels : list, optional
        List of labels to plot
    colors : list, optional
        List of colors for each cluster
    channel : int, optional
        Energy channel to use (None = sum)
    max_labels : int
        Maximum number of clusters to overlay
    frame_height : int
        Plot height
    frame_width : int
        Plot width
    colorbar_width : int
        Colorbar width
    colorbar_spacing : int
        Spacing between colorbars
    colorbar_position : str
        Position of colorbar
    colorbar_side : str
        Side to place colorbar column
    """
    # Obtener clustering
    if clustering is None:
        if hdbscan_results is None:
            raise ValueError("No clustering provided and hdbscan_results is missing.")
        clustering = hdbscan_results.labels_.reshape(data.shape[0], data.shape[1])

    # Intensidad
    if channel is None:
        intensity_map = data.sum(axis=-1)
    else:
        intensity_map = data[..., channel]

    # Labels a mostrar
    unique = [lab for lab in np.unique(clustering) if lab != -1]
    if labels is None:
        labels = unique[:max_labels]
    else:
        labels = [lab for lab in labels if lab in unique][:max_labels]

    # Colores por defecto si no se pasan
    if colors is None:
        colors = ["#FFFAF9", "#FFFEFB", "#FAF4FF", "#F3F6FF", "#7AC4B8", "#F3E8F0"]
    # Asegurar que hay suficientes colores
    if len(colors) < len(labels):
        colors = (colors * ((len(labels) // len(colors)) + 1))[:len(labels)]

    layers = []
    colorbars = []
    shape = clustering.shape
    
    # Hook para hacer transparente el fondo y el borde del mini-plot del colorbar
    def _transparent_bg(plot, element):
        p = plot.state
        try:
            p.background_fill_alpha = 0
            p.border_fill_alpha = 0
            p.outline_line_alpha = 0
            p.min_border = 0
            p.min_border_top = 0
            p.min_border_bottom = 0
            p.min_border_left = 0
            p.min_border_right = 0
            p.toolbar_location = None
        except Exception:
            pass
            
    for lab, col in zip(labels, colors):
        mask = (clustering == lab)
        if not np.any(mask):
            continue
        arr = np.where(mask, intensity_map, np.nan)

        # generar cmap tintado compatible con Holoviews/Bokeh
        try:
            cmap = get_tinted_grey_cmap(col).colors
        except Exception:
            cmap = col

        # clim sólo con valores del cluster
        valid = arr[np.isfinite(arr)]
        if valid.size > 0:
            clim = (np.nanmin(valid), np.nanmax(valid))
        else:
            clim = (0, 1)

        img = hv.Image(
            xr.Dataset(
                {f'Cluster_{lab}': (['y', 'x'], arr)},
                coords={'x': np.arange(shape[1]), 'y': np.arange(shape[0])}
            ),
            kdims=['x', 'y']
        ).opts(
            xaxis=None, yaxis=None, colorbar=False, toolbar='right',
            invert_yaxis=True, aspect='equal', frame_height=frame_height, frame_width=frame_width,
            cmap=cmap, clim=clim, bgcolor='black'
        ).relabel(f"cluster {lab}")

        layers.append(img)

        # Crear un colorbar específico para este cluster usando un HeatMap invisible
        cbar = hv.HeatMap([(0, 0, clim[0]), (0, 1, clim[1])]).opts(
            cmap=cmap,
            clim=clim,
            colorbar=True,
            colorbar_position=colorbar_position,
            colorbar_opts={'title': f'cluster {lab}', 'orientation': 'vertical'},
            xaxis=None,
            yaxis=None,
            show_frame=False,
            alpha=0,
            frame_height=frame_height,
            frame_width=0,
            toolbar='disable',
            margin=(colorbar_spacing, 0, colorbar_spacing, 0),
            padding=0,
            hooks=[_transparent_bg],
            shared_axes=False,
            axiswise=True,
        )
        colorbars.append(cbar)

    if not layers:
        raise RuntimeError("No hay capas para plotear (posibles labels vacíos).")

    overlay = hv.Overlay(layers).opts(shared_axes=True)

    # Disponer los colorbars en una columna fija usando bokeh layouts
    if colorbars:
        overlay_fig = hv.render(overlay, backend='bokeh')
        cbar_figs = [hv.render(cb, backend='bokeh') for cb in colorbars]
        cbar_column = row(*cbar_figs, sizing_mode='fixed')
        
        if str(colorbar_side).lower() == 'right':
            layout = row(overlay_fig, cbar_column)
        else:
            layout = row(cbar_column, overlay_fig)
        show(layout)
    else:
        show(hv.render(overlay, backend='bokeh'))
